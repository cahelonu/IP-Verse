"""Unit tests. They never touch the internet: every API call is mocked.

Run from the project root with:  python -m unittest discover -v
"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import requests

from ip_verse_app import api_client, cli, formatter, report


def fake_response(payload, status=200):
    """Build a stand-in for a requests.Response."""
    response = mock.Mock()
    response.status_code = status
    response.ok = status < 400
    response.json.return_value = payload
    return response


IPAPI_SAMPLE = {
    "ip": "8.8.8.8",
    "network": "8.8.8.0/24",
    "city": "Mountain View",
    "region": "California",
    "country_name": "United States",
    "country_code": "US",
    "postal": "94043",
    "latitude": 37.386,
    "longitude": -122.0838,
    "timezone": "America/Los_Angeles",
    "utc_offset": "-0800",
    "asn": "AS15169",
    "org": "GOOGLE",
}

#Test suite verifying IP address scope classification (Global, Private, Loopback, Link-local, Multicast)
class ClassifyAddressTests(unittest.TestCase):
    def test_known_scopes(self):
        cases = {
            "8.8.8.8": api_client.SCOPE_GLOBAL,
            "2001:4860:4860::8888": api_client.SCOPE_GLOBAL,
            "192.168.1.10": "Private / reserved",
            "10.0.0.1": "Private / reserved",
            "127.0.0.1": "Loopback",
            "::1": "Loopback",
            "169.254.10.10": "Link-local",
            "fe80::1": "Link-local",
            "224.0.0.1": "Multicast",
            "ff02::1": "Multicast",
        }
        for address, expected in cases.items():
            with self.subTest(address=address):
                self.assertEqual(api_client.classify_address(address), expected)


class ApiClientTests(unittest.TestCase):
    @mock.patch("ip_address_app.api_client.requests.get")
    def test_fetch_public_ip_v4(self, get):
        get.return_value = fake_response({"ip": "203.0.113.7"})
        self.assertEqual(api_client.fetch_public_ip(4), "203.0.113.7")
#Ensure IPLookupError is raised when an IPv4 address is returned for an IPv6 request
    @mock.patch("ip_address_app.api_client.requests.get")
    def test_fetch_public_ip_rejects_wrong_version(self, get):
        get.return_value = fake_response({"ip": "203.0.113.7"})
        with self.assertRaises(api_client.IPLookupError):
            api_client.fetch_public_ip(6)
#Ensure malformed or non-IP strings from the API trigger an IPLookupError
    @mock.patch("ip_address_app.api_client.requests.get")
    def test_fetch_public_ip_rejects_garbage(self, get):
        get.return_value = fake_response({"ip": "not-an-ip"})
        with self.assertRaises(api_client.IPLookupError):
            api_client.fetch_public_ip(4)
#Verify network connection failures are caught and converted to IPLookupError
    @mock.patch("ip_address_app.api_client.requests.get")
    def test_connection_error_becomes_lookup_error(self, get):
        get.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaises(api_client.IPLookupError):
            api_client.fetch_public_ip(6)
#Verify request timeouts raise an IPLookupError containing a clear timeout message
    @mock.patch("ip_address_app.api_client.requests.get")
    def test_timeout_becomes_lookup_error(self, get):
        get.side_effect = requests.exceptions.Timeout()
        with self.assertRaisesRegex(api_client.IPLookupError, "timed out"):
            api_client.fetch_public_ip(4)
#Ensure HTTP 429 responses raise a user-friendly rate limit error
    @mock.patch("ip_address_app.api_client.requests.get")
    def test_rate_limit_message(self, get):
        get.return_value = fake_response({}, status=429)
        with self.assertRaisesRegex(api_client.IPLookupError, "rate limit"):
            api_client.fetch_ip_details("8.8.8.8")
#check
    @mock.patch("ip_address_app.api_client.requests.get")
    def test_fetch_ip_details_normalises_fields(self, get):
        get.return_value = fake_response(IPAPI_SAMPLE)
        record = api_client.fetch_ip_details("8.8.8.8")
        self.assertEqual(record["isp"], "GOOGLE")
        self.assertEqual(record["asn"], "AS15169")
        self.assertEqual(record["country_code"], "US")
        self.assertEqual(record["version"], 4)
        self.assertEqual(record["scope"], api_client.SCOPE_GLOBAL)

    @mock.patch("ip_address_app.api_client.requests.get")
    def test_error_body_raises(self, get):
        get.return_value = fake_response({"error": True, "reason": "RateLimited"})
        with self.assertRaisesRegex(api_client.IPLookupError, "RateLimited"):
            api_client.fetch_ip_details("8.8.8.8")

#Test suite verifying report assembly, fallback handling, and JSON file export
class ReportTests(unittest.TestCase):
    @mock.patch("ip_address_app.report.fetch_ip_details")
    @mock.patch("ip_address_app.report.fetch_public_ip")
    def test_dual_stack(self, fetch_ip, fetch_details):
        fetch_ip.side_effect = lambda v: "8.8.8.8" if v == 4 else "2001:4860:4860::8888"
        fetch_details.side_effect = lambda ip: api_client.normalize_details(ip, IPAPI_SAMPLE)
        result = report.build_report()
        self.assertEqual(result["connectivity"], "Dual-stack (IPv4 and IPv6)")
        self.assertEqual(result["ipv4"]["ip"], "8.8.8.8")
        self.assertEqual(result["ipv6"]["version"], 6)
        self.assertEqual(result["notes"], [])
# Verify IPv6 failure degrades gracefully to an IPv4-only report with an explanatory note
    @mock.patch("ip_address_app.report.fetch_ip_details")
    @mock.patch("ip_address_app.report.fetch_public_ip")
    def test_ipv6_missing_is_a_note_not_a_crash(self, fetch_ip, fetch_details):
        def side_effect(version):
            if version == 6:
                raise api_client.IPLookupError("could not connect")
            return "8.8.8.8"

        fetch_ip.side_effect = side_effect
        fetch_details.side_effect = lambda ip: api_client.normalize_details(ip, IPAPI_SAMPLE)
        result = report.build_report()
        self.assertIsNone(result["ipv6"])
        self.assertIn("IPv4 only", result["connectivity"])
        self.assertTrue(any("IPv6" in note for note in result["notes"]))
#Verify partial report still displays the IP address even if geolocation lookup fails
    @mock.patch("ip_address_app.report.fetch_ip_details")
    def test_details_failure_keeps_the_address(self, fetch_details):
        fetch_details.side_effect = api_client.IPLookupError("rate limit")
        result = report.build_report(ip="8.8.8.8")
        self.assertEqual(result["ipv4"]["ip"], "8.8.8.8")
        self.assertIsNone(result["ipv4"]["isp"])
        self.assertEqual(len(result["notes"]), 1)
#Ensure private/local IP addresses are classified locally without leaking to external APIs
    @mock.patch("ip_address_app.report.fetch_ip_details")
    def test_private_address_is_not_sent_to_the_api(self, fetch_details):
        result = report.build_report(ip="192.168.1.10")
        fetch_details.assert_not_called()
        self.assertEqual(result["ipv4"]["scope"], "Private / reserved")
#Verify invalid user-supplied IP addresses are rejected before making network calls
    def test_invalid_address_is_rejected(self):
        with self.assertRaises(api_client.IPLookupError):
            report.build_report(ip="999.1.1.1")

    def test_save_report_writes_valid_json(self):
        data = {"ipv4": None, "ipv6": None, "notes": []}
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "out.json")
            report.save_report(data, path)
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(json.load(handle), data)

#Test suite verifying ASCII table alignment, ANSI color toggles, and JSON serialization
class FormatterTests(unittest.TestCase):
    def setUp(self):
        record = api_client.normalize_details("8.8.8.8", IPAPI_SAMPLE)
        self.sample = {
            "generated_at": "2026-11-15T06:00:00+00:00",
            "mode": "my-ip",
            "ipv4": record,
            "ipv6": None,
            "connectivity": "IPv4 only (no IPv6 connectivity detected)",
            "notes": ["No public IPv6 address found."],
        }

    def test_plain_output_has_no_color_codes(self):
        text = formatter.render_report(self.sample, use_color=False)
        self.assertNotIn("\033[", text)
        self.assertIn("GOOGLE", text)
        self.assertIn("AS15169", text)

    def test_color_output_has_color_codes(self):
        self.assertIn("\033[", formatter.render_report(self.sample, use_color=True))

    def test_table_lines_are_aligned(self):
        rows = formatter.build_rows(self.sample["ipv4"])
        table = formatter.render_table("IPv4 ADDRESS", rows).splitlines()
        self.assertEqual(len({len(line) for line in table}), 1)

    def test_missing_values_show_na(self):
        record = api_client.normalize_details("8.8.8.8")
        values = dict(formatter.build_rows(record))
        self.assertEqual(values["ISP / Organization"], formatter.NA)

    def test_json_round_trip(self):
        self.assertEqual(json.loads(formatter.to_json(self.sample)), self.sample)

#Test suite verifying CLI argument parsing, file saving, and exit status codes
class CliTests(unittest.TestCase):
    def setUp(self):
        record = api_client.normalize_details("8.8.8.8", IPAPI_SAMPLE)
        self.sample = {
            "generated_at": "2026-11-15T06:00:00+00:00",
            "mode": "my-ip",
            "ipv4": record,
            "ipv6": None,
            "connectivity": "IPv4 only",
            "notes": [],
        }

    def run_cli(self, argv, built=None):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("ip_address_app.cli.build_report", return_value=built or self.sample):
            with redirect_stdout(out), redirect_stderr(err):
                code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_default_run(self):
        code, out, _ = self.run_cli([])
        self.assertEqual(code, 0)
        self.assertIn("IPv4 ADDRESS", out)

    def test_json_flag_prints_valid_json(self):
        code, out, _ = self.run_cli(["--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["ipv4"]["ip"], "8.8.8.8")

    def test_save_flag_writes_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "r.json")
            code, _, err = self.run_cli(["--save", path])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(path))
            self.assertIn("saved", err)

    def test_exit_code_1_when_nothing_found(self):
        empty = dict(self.sample, ipv4=None)
        code, _, _ = self.run_cli([], built=empty)
        self.assertEqual(code, 1)

    def test_exit_code_2_for_invalid_ip(self):
        err = io.StringIO()
        with redirect_stderr(err):
            code = cli.main(["--ip", "banana"])
        self.assertEqual(code, 2)
        self.assertIn("not a valid", err.getvalue())

    def test_flags_are_passed_to_build_report(self):
        with mock.patch("ip_address_app.cli.build_report", return_value=self.sample) as build:
            with redirect_stdout(io.StringIO()):
                cli.main(["-4"])
        build.assert_called_once_with(ip=None, want_v4=True, want_v6=False)


if __name__ == "__main__":
    unittest.main()
