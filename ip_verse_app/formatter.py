"""Presentation layer: turn a report dictionary into text.

Two outputs are supported:
* render_report() : coloured ASCII tables for the terminal.
* to_json()       : machine readable JSON.

Colours use plain ANSI escape codes, so no extra library is needed. They work
in the VSCode terminal, macOS/Linux terminals and Windows 10+ (cli.py switches
ANSI support on for Windows). Use --no-color or the NO_COLOR environment
variable to turn them off. Piped output is never coloured.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

NA = "N/A"  # shown when the API gave no value

# ANSI colour codes.
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"


def paint(text: str, style: str, enabled: bool) -> str:
    """Wrap `text` in a colour code when colour is enabled."""
    return f"{style}{text}{RESET}" if enabled else text


def _show(value: Any) -> str:
    """Convert any value to display text, using N/A for empty values."""
    return NA if value in (None, "") else str(value)


def build_rows(record: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Choose which fields appear in a table and in which order.

    To show a new field, add it here (and to normalize_details in
    api_client.py if it is new data).
    """
    lat, lon = record.get("latitude"), record.get("longitude")
    coordinates = f"{lat}, {lon}" if lat is not None and lon is not None else NA
    return [
        ("IP address", _show(record["ip"])),
        ("Version", f"IPv{record['version']}"),
        ("Scope", _show(record.get("scope"))),
        ("Network (CIDR)", _show(record.get("network"))),
        ("ISP / Organization", _show(record.get("isp"))),
        ("ASN", _show(record.get("asn"))),
        ("City", _show(record.get("city"))),
        ("Region", _show(record.get("region"))),
        ("Country", _show(record.get("country_name"))),
        ("Country code", _show(record.get("country_code"))),
        ("Postal code", _show(record.get("postal"))),
        ("Coordinates", coordinates),
        ("Time zone", _show(record.get("timezone"))),
        ("UTC offset", _show(record.get("utc_offset"))),
    ]


def render_table(title: str, rows: List[Tuple[str, str]], use_color: bool = False,
                 title_style: str = BOLD + YELLOW) -> str:
    """Draw one boxed table.

    Widths are measured on the plain text first and colour is added after
    padding, because invisible colour codes would break the alignment.
    """
    label_w = max(len(label) for label, _ in rows)
    inner = max(label_w + max(len(v) for _, v in rows) + 3, len(title))
    value_w = inner - label_w - 3

    border = "+" + "-" * (inner + 2) + "+"
    lines = [border, "| " + paint(title.center(inner), title_style, use_color) + " |", border]
    for label, value in rows:
        label_cell = paint(label.ljust(label_w), CYAN, use_color)
        if label == "IP address":
            value_cell = paint(value.ljust(value_w), BOLD + GREEN, use_color)
        elif value == NA:
            value_cell = paint(value.ljust(value_w), DIM, use_color)
        else:
            value_cell = value.ljust(value_w)
        lines.append(f"| {label_cell} | {value_cell} |")
    lines.append(border)
    return "\n".join(lines)


def render_report(report: Dict[str, Any], use_color: bool = False) -> str:
    """Return the complete terminal output for a report."""
    parts: List[str] = [paint("IPv4 / IPv6 Address Application", BOLD, use_color)]

    for key, title, style in (
        ("ipv4", "IPv4 ADDRESS", BOLD + YELLOW),
        ("ipv6", "IPv6 ADDRESS", BOLD + MAGENTA),
    ):
        record = report.get(key)
        if record:
            parts.append(render_table(title, build_rows(record), use_color, style))

    parts.append(f"Connectivity : {paint(report['connectivity'], BOLD, use_color)}")
    parts.append(f"Generated    : {report['generated_at']} (UTC)")
    for note in report.get("notes", []):
        parts.append(paint(f"Note: {note}", RED, use_color))
    return "\n\n".join(parts)


def to_json(report: Dict[str, Any]) -> str:
    """Return the report as indented JSON text."""
    return json.dumps(report, indent=2, ensure_ascii=False)
