"""Command-line entry point.

    khanyo                      launch the GUI
    khanyo --list-tools         list every tool
    khanyo --report html        build a support report without opening the GUI
"""

import argparse
import os
import sys
from datetime import datetime
from typing import List, Optional

from . import __version__
from .config import IS_WINDOWS, REPORTS_DIR
from .core import open_path
from .findings import run_all_checks
from .registry import CATEGORIES, REPORT_TOOLS
from .reports import collect_sections, default_report_name, render, write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="khanyo",
        description="Khanyo IT Toolkit -- a Windows PC troubleshooting toolkit.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--list-tools", action="store_true", help="list all tools and exit")
    parser.add_argument(
        "--report",
        choices=["txt", "html", "json"],
        help="generate a support report without opening the GUI",
    )
    parser.add_argument("--report-history", action="store_true", help="list recently saved reports")
    parser.add_argument("--open-last-report", action="store_true", help="open the newest saved report")
    parser.add_argument("--limit", type=int, default=10, help="number of recent reports to show with --report-history")
    parser.add_argument("-o", "--output", help="where to save the report (use with --report)")
    parser.add_argument("--client", help="client name to include at the top of the report")
    parser.add_argument("--ticket", help="support ticket number to include at the top of the report")
    parser.add_argument("--technician", help="technician name to include at the top of the report")
    parser.add_argument("--notes", help="support notes to include at the top of the report")
    parser.add_argument("--redact", action="store_true", help="mask host/device identity data in exported content")
    return parser


def _list_tools() -> int:
    for category, tools in CATEGORIES.items():
        print(f"\n[{category}]")
        for tool in tools:
            flag = "  (changes system state)" if tool.dangerous else ""
            print(f"  {tool.label:<28} {tool.tooltip}{flag}")
    return 0


def _list_recent_reports(limit: int = 10) -> int:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    entries = []
    for name in os.listdir(REPORTS_DIR):
        path = os.path.join(REPORTS_DIR, name)
        if os.path.isfile(path) and name.lower().endswith((".txt", ".html", ".json")):
            entries.append((os.path.getmtime(path), name, path))
    if not entries:
        print(f"No saved reports found in: {REPORTS_DIR}")
        return 0
    ordered = sorted(entries, key=lambda item: (-item[0], item[1]))
    for _, name, path in ordered[: max(0, limit)]:
        modified = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{modified}  {name}")
    return 0


def _open_last_report() -> int:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    entries = []
    for name in os.listdir(REPORTS_DIR):
        path = os.path.join(REPORTS_DIR, name)
        if os.path.isfile(path) and name.lower().endswith((".txt", ".html", ".json")):
            entries.append((os.path.getmtime(path), name, path))
    if not entries:
        print(f"No saved reports found in: {REPORTS_DIR}")
        return 0
    _, _, latest = sorted(entries, key=lambda item: (-item[0], item[1]))[0]
    print(latest)
    if open_path(latest):
        print(f"Opened latest report: {latest}")
    else:
        print(f"Could not open latest report: {latest}")
    return 0


def _make_report(
    fmt: str,
    output: Optional[str],
    *,
    client: Optional[str] = None,
    ticket: Optional[str] = None,
    technician: Optional[str] = None,
    notes: Optional[str] = None,
    redact: bool = False,
) -> int:
    path = output or os.path.join(REPORTS_DIR, default_report_name(fmt))
    findings = run_all_checks()
    sections = collect_sections(
        REPORT_TOOLS, progress=lambda label: print(f"Collecting: {label} ...", file=sys.stderr)
    )
    payload = render(
        sections,
        fmt,
        findings=findings,
        client=client,
        ticket=ticket,
        technician=technician,
        notes=notes,
        redact=redact,
    )
    write_report(path, payload)
    print(f"Support report saved to: {path}")
    return 0


def _launch_gui() -> int:
    if not IS_WINDOWS:
        print("Warning: this toolkit is designed for Windows. "
              "Some commands will not work as expected on this OS.", file=sys.stderr)
    try:
        from .app import run_gui
    except ImportError as e:  # tkinter missing (e.g. minimal Linux installs)
        print(f"Could not start the GUI: {e}", file=sys.stderr)
        return 1
    run_gui()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.output and not args.report:
        parser.error("--output can only be used together with --report")
    if args.list_tools:
        return _list_tools()
    if args.report_history:
        return _list_recent_reports(limit=args.limit)
    if args.open_last_report:
        return _open_last_report()
    if args.report:
        return _make_report(
            args.report,
            args.output,
            client=args.client,
            ticket=args.ticket,
            technician=args.technician,
            notes=args.notes,
            redact=args.redact,
        )
    return _launch_gui()
