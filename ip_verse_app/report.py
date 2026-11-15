from __future__ import annotations

import ipaddress
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .api_client import (
    SCOPE_GLOBAL,
    IPLookupError,
    classify_address,
    fetch_ip_details,
    fetch_public_ip,
    normalize_details,
)

def _describe(address: str, notes: List[str]) -> Dict[str, Any]:
    # Return the detail record for one (1) address.

    # Non-public addresses (192.168.x.x, fe80::, ...) are not sent to the API, because geolocation makes no sense for them and it saves the rate limit.
    # If the API fails we still return a record with the address and its scope, and add a note so the user knows why the details are missing.

    scope = classify_address(address)
    if scope != SCOPE_GLOBAL:
        notes.append(f"{address} is a {scope.lower()} address, so no ISP or location exists for it.")
        return normalize_details(address)
    try:
        return fetch_ip_details(address)
    except IPLookupError as exc:
        notes.append(f"Details for {address} are unavailable: {exc}.")
        return normalize_details(address)

def _connectivity(report: Dict[str, Any], lookup_mode: bool, want_v4: bool, want_v6: bool) -> str:
    """Write the one-line summary shown under the tables."""
    if lookup_mode:
        return "Lookup of a single address"
    has_v4, has_v6 = report["ipv4"] is not None, report["ipv6"] is not None
    if want_v4 and want_v6:
        if has_v4 and has_v6:
            return "Dual-stack (IPv4 and IPv6)"
        if has_v4:
            return "IPv4 only (no IPv6 connectivity detected)"
        if has_v6:
            return "IPv6 only (no IPv4 connectivity detected)"
        return "No public address found"
    wanted = "IPv4" if want_v4 else "IPv6"
    return f"{wanted} checked only (as requested)"

def build_report(
    ip: Optional[str] = None, want_v4: bool = True, want_v6: bool = True
) -> Dict[str, Any]:
    """Create the full report.

    ip      : when given, look up that address instead of this computer's own.
    want_v4 : include the IPv4 part (ignored when `ip` is given).
    want_v6 : include the IPv6 part (ignored when `ip` is given).

    Raises IPLookupError only when `ip` is not a valid address. Every network
    problem is turned into a note inside the report instead.
    """
    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "lookup" if ip is not None else "my-ip",
        "ipv4": None,
        "ipv6": None,
        "connectivity": "",
        "notes": [],
    }
    notes: List[str] = report["notes"]

    # Step 1: decide which addresses to describe.
    addresses: Dict[int, str] = {}
    if ip is not None:
        try:
            parsed = ipaddress.ip_address(ip.strip())
        except ValueError:
            raise IPLookupError(f"'{ip}' is not a valid IPv4 or IPv6 address")
        addresses[parsed.version] = str(parsed)
    else:
        for version, wanted in ((4, want_v4), (6, want_v6)):
            if not wanted:
                continue
            try:
                addresses[version] = fetch_public_ip(version)
            except IPLookupError as exc:
                hint = " Your network or ISP may not offer IPv6." if version == 6 else ""
                notes.append(f"No public IPv{version} address found: {exc}.{hint}")

    # Step 2: describe each address.
    for version, address in addresses.items():
        report[f"ipv{version}"] = _describe(address, notes)

    report["connectivity"] = _connectivity(report, ip is not None, want_v4, want_v6)
    return report

def save_report(report: Dict[str, Any], path: str) -> None:
    """Write the report to `path` as pretty JSON. Raises OSError on failure."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")