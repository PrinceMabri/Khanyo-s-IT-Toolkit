"""Support report generation. Pure functions -- no GUI code in here."""

import html
import json
import os
import re
import socket
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .core import header
from .findings import Finding
from .registry import REPORT_TOOLS, Tool

Section = Tuple[str, str]


def redact_text(value: str) -> str:
    """Mask common identity values from support output before sharing or exporting."""
    text = str(value or "")
    patterns = [
        (
            r"(?i)\b(host|ipv4|mac|user(?:name)?|username|computer)\s*[:=]\s*[^\n]+",
            lambda m: f"{m.group(1)}: [REDACTED]",
        ),
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED_IP]"),
        (r"(?i)\b(?:PC|HOST|DESKTOP|LAPTOP)[-_]?[A-Z0-9-]*\d+\b", "[REDACTED_HOST]"),
        (r"(?i)\b[0-9A-F]{2}(?:[:-][0-9A-F]{2}){5}\b", "[REDACTED_MAC]"),
        (r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", "[REDACTED_EMAIL]"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def collect_sections(
    tools: Sequence[Tool] = REPORT_TOOLS,
    progress: Optional[Callable[[str], None]] = None,
) -> List[Section]:
    """Run each tool and return [(label, output)]. A failing tool never aborts the report."""
    sections: List[Section] = []
    for tool in tools:
        if progress:
            progress(tool.label)
        try:
            sections.append((tool.label, tool.func()))
        except Exception as e:
            sections.append((tool.label, f"Error: {e}"))
    return sections


def default_report_name(fmt: str) -> str:
    return f"khanyo_support_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{fmt}"


def _findings_summary(findings: Sequence[Finding]) -> str:
    if not findings:
        return "Findings Summary\nNo findings available."
    lines = ["FINDINGS SUMMARY"]
    for item in findings:
        badge = item.severity.name
        lines.append(f"[{badge}] {item.title}: {item.detail}")
    return "\n".join(lines)


def _ticket_metadata_lines(
    client: Optional[str] = None,
    ticket: Optional[str] = None,
    technician: Optional[str] = None,
    notes: Optional[str] = None,
) -> List[Tuple[str, str]]:
    metadata = [
        ("Client", client),
        ("Ticket", ticket),
        ("Technician", technician),
        ("Notes", notes),
    ]
    return [(label, value) for label, value in metadata if value]


def _apply_redaction(value: Optional[str], redact: bool) -> Optional[str]:
    if not redact or value is None:
        return value
    return redact_text(value)


def render_txt(
    sections: Sequence[Section],
    findings: Optional[Sequence[Finding]] = None,
    *,
    client: Optional[str] = None,
    ticket: Optional[str] = None,
    technician: Optional[str] = None,
    notes: Optional[str] = None,
    redact: bool = False,
) -> str:
    lines = [header("KHANYO IT TOOLKIT -- SUPPORT REPORT")]
    metadata = _ticket_metadata_lines(client, ticket, technician, notes)
    if metadata:
        lines.append("TICKET DETAILS")
        for label, value in metadata:
            lines.append(f"{label}: {_apply_redaction(value, redact)}")
        lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Machine:   {socket.gethostname()}\n")
    lines.append(_findings_summary(findings or []))
    lines.append("")
    for _label, content in sections:
        lines.append(_apply_redaction(content, redact))
    return "\n".join(lines)


def render_html(
    sections: Sequence[Section],
    findings: Optional[Sequence[Finding]] = None,
    *,
    client: Optional[str] = None,
    ticket: Optional[str] = None,
    technician: Optional[str] = None,
    notes: Optional[str] = None,
    redact: bool = False,
) -> str:
    rows = "".join(
        (
            f"<section><h2>{html.escape(label)}</h2>"
            f"<pre>{html.escape(_apply_redaction(content, redact) or '')}</pre></section>"
        )
        for label, content in sections
    )
    summary_items = "".join(
        (
            f"<li><strong>[{html.escape(item.severity.name)}]</strong> "
            f"{html.escape(item.title)}: {html.escape(item.detail)}</li>"
        )
        for item in (findings or [])
    )
    if not summary_items:
        summary_items = "<li>No findings available.</li>"
    generated = html.escape(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    machine = html.escape(socket.gethostname())

    metadata_items = []
    for label, value in _ticket_metadata_lines(client, ticket, technician, notes):
        safe = html.escape(_apply_redaction(value, redact) or "")
        metadata_items.append(f"<li><strong>{html.escape(label)}:</strong> {safe}</li>")
    if not metadata_items:
        metadata_items = ["<li>No ticket metadata provided.</li>"]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Khanyo IT Toolkit -- Support Report</title>
<style>
  body {{ background:#151922; color:#e6e9ef; font-family: Segoe UI, Arial, sans-serif; margin:0; padding:32px; }}
  h1 {{ color:#e8b64c; margin-bottom:4px; }}
  .meta {{ color:#8b93a3; margin-bottom:12px; }}
  .ticket-meta {{ background:#1f2430; border-radius:8px; padding:16px 20px; margin-bottom:16px; }}
  .summary {{ background:#1f2430; border-radius:8px; padding:16px 20px; margin-bottom:16px; }}
  section {{ background:#1f2430; border-radius:8px; padding:16px 20px; margin-bottom:16px; }}
  h2 {{ color:#e8b64c; font-size:15px; margin:0 0 10px 0; border-bottom:1px solid #2c3444; padding-bottom:6px; }}
  pre {{ white-space:pre-wrap; word-break:break-word; font-family: Consolas, monospace;
        font-size:12.5px; color:#d7dce3; margin:0; }}
  @media print {{
    body {{ background:#fff; color:#111; }}
    .ticket-meta, .summary, section {{ background:#fff; color:#111; border:1px solid #ccc; }}
    .meta {{ color:#444; }}
  }}
</style>
</head>
<body>
  <h1>&#10022; Khanyo IT Toolkit -- Support Report</h1>
  <div class="meta">Generated {generated} &middot; Machine: {machine}</div>
  <div class="ticket-meta"><h2>Ticket Details</h2><ul>{''.join(metadata_items)}</ul></div>
  <div class="summary"><h2>Findings Summary</h2><ul>{summary_items}</ul></div>
  {rows}
</body>
</html>"""


def render_json(
    sections: Sequence[Section],
    findings: Optional[Sequence[Finding]] = None,
    *,
    client: Optional[str] = None,
    ticket: Optional[str] = None,
    technician: Optional[str] = None,
    notes: Optional[str] = None,
    redact: bool = False,
) -> str:
    payload: Dict[str, Any] = {
        "metadata": {
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "machine": socket.gethostname(),
            "client": _apply_redaction(client, redact),
            "ticket": _apply_redaction(ticket, redact),
            "technician": _apply_redaction(technician, redact),
            "notes": _apply_redaction(notes, redact),
        },
        "findings": [
            {
                "severity": item.severity.name,
                "title": item.title,
                "detail": _apply_redaction(item.detail, redact),
                "source_tool": item.source_tool,
            }
            for item in (findings or [])
        ],
        "sections": [
            {"label": label, "content": _apply_redaction(content, redact)}
            for label, content in sections
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)


def render(
    sections: Sequence[Section],
    fmt: str,
    findings: Optional[Sequence[Finding]] = None,
    *,
    client: Optional[str] = None,
    ticket: Optional[str] = None,
    technician: Optional[str] = None,
    notes: Optional[str] = None,
    redact: bool = False,
) -> str:
    if fmt == "json":
        return render_json(
            sections,
            findings,
            client=client,
            ticket=ticket,
            technician=technician,
            notes=notes,
            redact=redact,
        )
    if fmt == "html":
        return render_html(
            sections,
            findings,
            client=client,
            ticket=ticket,
            technician=technician,
            notes=notes,
            redact=redact,
        )
    return render_txt(
        sections,
        findings,
        client=client,
        ticket=ticket,
        technician=technician,
        notes=notes,
        redact=redact,
    )


def write_report(path: str, content: str) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
