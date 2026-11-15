# IPv4/IPv6 Address Application

A Python command-line prototype for network technicians. It shows this computer's current **public IPv4 and IPv6 addresses** together with the ISP, ASN, network, country code and geolocation, drawn as a colour-coded table. It was built for Project Activity 3 (Social Coding), Option 2.

## Quick start

```bash
git clone <repository-url>
cd ip-address-app
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Usage

| Command | What it does |
| --- | --- |
| `python main.py` | Shows your own public IPv4 and IPv6 details |
| `python main.py -4` / `-6` | Checks only IPv4 or only IPv6 |
| `python main.py --ip 8.8.8.8` | Looks up any IPv4 or IPv6 address |
| `python main.py --json` | Prints JSON instead of tables |
| `python main.py --save report.json` | Also saves the report to a file |
| `python main.py --no-color` | Turns colours off |

Exit codes: `0` success, `1` nothing found or file could not be saved, `2` invalid input.

## Features

1. Detects public IPv4 and IPv6 separately, so it shows whether the network is dual-stack, IPv4 only or IPv6 only.
2. Shows ISP/organisation, ASN, network (CIDR), city, region, country, country code, postal code, coordinates, time zone and UTC offset.
3. Classifies each address (global, private, loopback, link-local, multicast) using Python's `ipaddress` module, and skips the API for non-public addresses.
4. Validates every address returned by an API and every address typed by the user.
5. Friendly handling of timeouts, no connection, rate limits and bad responses. IPv6 being unavailable is a note, not a crash.
6. Output as coloured ASCII tables, JSON, or a saved JSON file.

## How it works

```
main.py -> cli.py -> report.py -> api_client.py   (network calls and normalising)
                  \-> formatter.py                 (tables and JSON text)
```

| File | Purpose |
| --- | --- |
| `ip_address_app/api_client.py` | Calls ipify (own address) and ipapi.co (details). Converts every failure into `IPLookupError`. |
| `ip_address_app/report.py` | `build_report()` joins the calls into one dictionary. Network problems become notes in the report. |
| `ip_address_app/formatter.py` | `render_report()` draws tables, `to_json()` dumps JSON. No network code. |
| `ip_address_app/cli.py` | Reads arguments, prints the result, returns the exit code. |
| `tests/test_app.py` | 26 unit tests. All API calls are mocked, so they run offline. |

APIs used: `api.ipify.org` (IPv4), `api6.ipify.org` (IPv6), `ipapi.co/<ip>/json/` (details). All are free and need no key. The free ipapi.co tier is rate limited.

## Continuing the project

* Run the tests first: `python -m unittest discover -v`.
* To show a new field, add it to `normalize_details()` in `api_client.py` and to `build_rows()` in `formatter.py`.
* To change API provider, rewrite only `api_client.py` and keep the keys that `normalize_details()` returns.
* Open ideas are in the backlog below.

## Backlog (future enhancements)

1. Fall back to a second details provider when ipapi.co fails or is rate limited.
2. Cache results for a few minutes in a local file to protect the free rate limit.
3. GitHub Actions workflow that runs the tests on every pull request.
4. Interactive menu mode so technicians do not need to remember flags.
5. Bulk lookup from a text file of addresses, exported to CSV.
6. Reverse DNS (PTR record) and a simple latency check.
7. History file with a "what changed since last time" view.
8. Side-by-side IPv4 and IPv6 comparison of ISP and location.
9. Package with `pyproject.toml` so it installs as an `ip-address-app` command.
10. Optional API key support through an environment variable for higher rate limits.

## Team workflow

`main` is protected: nobody pushes to it directly. Each task lives on a `feature/<name>` branch, is merged through a pull request, and needs one teammate's review.
