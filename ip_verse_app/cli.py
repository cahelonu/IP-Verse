"""Command-line interface: reads arguments, runs the report, sets exit codes.

Exit codes (useful in scripts):
    0  at least one address was found and printed
    1  nothing could be found, or the --save file could not be written
    2  bad input, for example an invalid address passed to --ip
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from .api_client import IPLookupError
from .formatter import render_report, to_json
from .report import build_report, save_report


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Define and read the command-line options."""
    parser = argparse.ArgumentParser(
        prog="ip-address-app",
        description="Show your public IPv4 and IPv6 address with ISP, ASN and location.",
    )
    parser.add_argument("--ip", metavar="ADDRESS",
                        help="look up this IPv4/IPv6 address instead of your own")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("-4", "--ipv4-only", action="store_true", help="check IPv4 only")
    scope.add_argument("-6", "--ipv6-only", action="store_true", help="check IPv6 only")
    parser.add_argument("--json", action="store_true", help="print JSON instead of tables")
    parser.add_argument("--save", metavar="FILE", help="also save the report to FILE as JSON")
    parser.add_argument("--no-color", action="store_true", help="turn colours off")
    return parser.parse_args(argv)


def _color_enabled(args: argparse.Namespace) -> bool:
    """Colour only on a real terminal, and never when the user opted out."""
    return not args.no_color and "NO_COLOR" not in os.environ and sys.stdout.isatty()


def main(argv: Optional[List[str]] = None) -> int:
    """Run the program and return the exit code."""
    args = parse_args(argv)

    if os.name == "nt":
        os.system("")  # a Windows trick that switches on ANSI colour support

    try:
        report = build_report(ip=args.ip, want_v4=not args.ipv6_only, want_v6=not args.ipv4_only)
    except IPLookupError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(to_json(report))
    else:
        print(render_report(report, _color_enabled(args)))

    if args.save:
        try:
            save_report(report, args.save)
        except OSError as exc:
            print(f"Error: could not save the report: {exc}", file=sys.stderr)
            return 1
        print(f"Report saved to {args.save}", file=sys.stderr)  # stderr keeps --json output clean

    return 0 if (report["ipv4"] or report["ipv6"]) else 1
