"""What this module does
1. Finds the computer's current public IPv4 and IPv6 address (ipify API).
2. Looks up details for an address: ISP, ASN, network, location (ipapi.co).
3. Normalises the raw API answers into one predictable dictionary, so no
   other module needs to know which API provider was used.

Nothing here prints anything. Printing is the job of formatter.py.
To change API provider, only this file needs to change, as long as
normalize_details() keeps returning the same keys.

APIs used
* https://api.ipify.org?format=json   -> {"ip": "203.0.113.5"}      (IPv4 only)
* https://api6.ipify.org?format=json  -> {"ip": "2001:db8::1"}      (IPv6 only)
* https://ipapi.co/<ip>/json/         -> JSON with org, asn, city, ...

The free tier of ipapi.co is rate limited (HTTP 429 when exceeded).
"""

from __future__ import annotations

import ipaddress
from typing import Any, Dict, Optional

import requests # pyright: ignore[reportMissingModuleSource]

# One URL per IP version. The api6 host only answers over IPv6.
IPIFY_URLS = {
    4: "https://api.ipify.org?format=json",
    6: "https://api6.ipify.org?format=json",
}
IPAPI_URL = "https://ipapi.co/{ip}/json/"


REQUEST_TIMEOUT = 8

# ipapi.co rejects requests that have no User-Agent header.
HEADERS = {"User-Agent": "ip-address-app/1.0 (student project)"}

# Text returned by classify_address() for a normal public address.
SCOPE_GLOBAL = "Global (public)"

class IPLookupError(Exception):
    """Raised for any problem the user should be told about.

    Examples: no internet, timeout, rate limit, bad JSON, invalid address.
    The message is written for humans and can be printed as it is.
    """


def _get_json(url: str) -> Any:
    """Download a URL and return the decoded JSON.

    All low-level problems from the requests library are converted into
    IPLookupError with a friendly message, so callers only handle one type.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        raise IPLookupError(f"the request timed out after {REQUEST_TIMEOUT} seconds")
    except requests.exceptions.ConnectionError:
        raise IPLookupError("could not connect (check the internet connection)")
    except requests.exceptions.RequestException as exc:
        raise IPLookupError(f"the request failed: {exc}")

    if response.status_code == 429:
        raise IPLookupError(
            "the free API rate limit was reached, wait a few minutes and try again"
        )
    if not response.ok:
        raise IPLookupError(f"the server answered with HTTP {response.status_code}")

    try:
        return response.json()
    except ValueError:
        raise IPLookupError("the server did not return valid JSON")


def fetch_public_ip(version: int) -> str:
    """Return the computer's current public address for IP version 4 or 6.

    Raises IPLookupError when the address cannot be found. For version 6 this
    is normal on networks without IPv6, so callers should treat it as
    "not available" rather than as a crash.
    """
    if version not in IPIFY_URLS:
        raise ValueError("version must be 4 or 6")

    data = _get_json(IPIFY_URLS[version])
    raw = data.get("ip") if isinstance(data, dict) else None
    if not raw:
        raise IPLookupError("the service did not return an IP address")
    try:
        parsed = ipaddress.ip_address(raw)
    except ValueError:
        raise IPLookupError("the service did not return a valid IP address")
    if parsed.version != version:
        raise IPLookupError(f"expected an IPv{version} address but got IPv{parsed.version}")
    return str(parsed)


def classify_address(ip: str) -> str:
    """Describe what kind of address this is, using only the ipaddress module.

    No network access is needed. The order of the checks matters, because
    loopback and link-local addresses are also counted as "private" by Python.
    """
    address = ipaddress.ip_address(ip)
    if address.is_unspecified:
        return "Unspecified"
    if address.is_loopback:
        return "Loopback"
    if address.is_link_local:
        return "Link-local"
    if address.is_multicast:
        return "Multicast"
    if address.is_private:
        return "Private / reserved"
    if address.is_reserved:
        return "Reserved"
    if address.is_global:
        return SCOPE_GLOBAL
    return "Other"


def normalize_details(ip: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build the standard record used by the rest of the program.

    `data` is the raw ipapi.co answer. When it is None or empty (for example a
    private address, or the API is down) every detail is None and the
    formatter will show "N/A". The keys below are the contract between
    api_client.py and formatter.py, so keep them stable.
    """
    data = data or {}
    return {
        "ip": ip,
        "version": ipaddress.ip_address(ip).version,
        "scope": classify_address(ip),
        "network": data.get("network"),
        "isp": data.get("org"),
        "asn": data.get("asn"),
        "city": data.get("city"),
        "region": data.get("region"),
        "country_name": data.get("country_name"),
        "country_code": data.get("country_code"),
        "postal": data.get("postal"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "timezone": data.get("timezone"),
        "utc_offset": data.get("utc_offset"),
    }


def fetch_ip_details(ip: str) -> Dict[str, Any]:
    """Look up ISP, ASN and location for one public address."""
    data = _get_json(IPAPI_URL.format(ip=ip))
    if not isinstance(data, dict):
        raise IPLookupError("the details service returned an unexpected answer")
    if data.get("error"):
        reason = data.get("reason") or data.get("message") or "unknown error"
        raise IPLookupError(f"the details service reported: {reason}")
    return normalize_details(ip, data)