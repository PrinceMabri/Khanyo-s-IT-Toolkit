"""Structured health checks used by the dashboard and reports."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from .config import IS_WINDOWS
from .core import get_cpu_usage, get_memory_usage, get_primary_drive_health, ps


class Severity(Enum):
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class Finding:
    severity: Severity
    title: str
    detail: str
    source_tool: str = "system"


def get_uptime_days() -> float:
    if not IS_WINDOWS:
        return 0.0
    try:
        raw = ps(
            "([datetime]::Now - ((Get-CimInstance Win32_OperatingSystem).LastBootUpTime)).TotalDays"
        ).strip()
        if not raw:
            return 0.0
        return float(raw.splitlines()[-1])
    except (TypeError, ValueError, IndexError):
        return 0.0


def pending_reboot() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        raw = ps(
            "if (Test-Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\"
            "Component Based Servicing\\RebootPending') { 'true' } "
            "elseif (Test-Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\"
            "WindowsUpdate\\Auto Update\\RebootRequired') { 'true' } "
            "else { 'false' }"
        ).strip().lower()
        return raw in {"true", "1", "yes"}
    except Exception:
        return False


def critical_services_stopped() -> List[str]:
    if not IS_WINDOWS:
        return []
    try:
        raw = ps(
            "Get-Service -Name Dhcp,Dnscache,EventLog,Winmgmt,wuauserv -ErrorAction SilentlyContinue | "
            "Where-Object { $_.StartType -eq 'Automatic' -and $_.Status -ne 'Running' } | "
            "Select-Object -ExpandProperty Name"
        )
        services = [item.strip() for item in raw.splitlines() if item.strip()]
        return services
    except Exception:
        return []


def problem_devices_present() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        raw = ps(
            "Get-CimInstance Win32_PnPEntity | "
            "Where-Object { $_.ConfigManagerErrorCode -and $_.ConfigManagerErrorCode -ne 0 } | "
            "Select-Object -ExpandProperty Name"
        )
        return bool(raw.strip())
    except Exception:
        return False


def physical_disk_unhealthy() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        raw = ps(
            "Get-PhysicalDisk -ErrorAction SilentlyContinue | "
            "Where-Object { $_.HealthStatus -ne 'Healthy' } | "
            "Select-Object -ExpandProperty FriendlyName"
        )
        return bool(raw.strip())
    except Exception:
        return False


def firewall_disabled() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        raw = ps(
            "Get-NetFirewallProfile -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Enabled -eq $false } | "
            "Select-Object -ExpandProperty Name"
        )
        return bool(raw.strip())
    except Exception:
        return False


def defender_realtime_off() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        raw = ps(
            "(Get-MpPreference -ErrorAction SilentlyContinue).DisableRealtimeMonitoring"
        ).strip().lower()
        return raw in {"true", "1", "yes"}
    except Exception:
        return False


def _finding(severity: Severity, title: str, detail: str) -> Finding:
    return Finding(severity=severity, title=title, detail=detail, source_tool="system")


def run_all_checks() -> List[Finding]:
    if not IS_WINDOWS:
        return [
            _finding(
                Severity.OK,
                "Platform check",
                "This toolkit is intended for Windows. Findings are limited on non-Windows hosts.",
            )
        ]

    findings: List[Finding] = []

    try:
        cpu_pct = get_cpu_usage()
        if cpu_pct is None:
            findings.append(_finding(Severity.WARNING, "CPU usage", "could not check CPU usage"))
        elif cpu_pct > 90.0:
            findings.append(
                _finding(
                    Severity.WARNING,
                    "CPU usage high",
                    f"CPU usage is {cpu_pct:.1f}% (warning threshold: >90%).",
                )
            )
    except Exception:
        findings.append(_finding(Severity.WARNING, "CPU usage", "could not check CPU usage"))

    try:
        free_percent = get_primary_drive_health()
        if free_percent is None:
            findings.append(_finding(Severity.WARNING, "C: drive free space", "could not check C: free space"))
        elif free_percent < 8.0:
            findings.append(
                _finding(
                    Severity.CRITICAL,
                    "C: drive free space low",
                    f"C: drive free space is {free_percent:.1f}% (critical threshold: <8%).",
                )
            )
        elif free_percent < 15.0:
            findings.append(
                _finding(
                    Severity.WARNING,
                    "C: drive free space low",
                    f"C: drive free space is {free_percent:.1f}% (warning threshold: <15%).",
                )
            )
    except Exception:
        findings.append(_finding(Severity.WARNING, "C: drive free space", "could not check C: free space"))

    try:
        ram_pct = get_memory_usage()
        if ram_pct is None:
            findings.append(_finding(Severity.WARNING, "RAM usage", "could not check RAM usage"))
        elif ram_pct > 90.0:
            findings.append(
                _finding(
                    Severity.WARNING,
                    "RAM usage high",
                    f"RAM usage is {ram_pct:.1f}% (warning threshold: >90%).",
                )
            )
    except Exception:
        findings.append(_finding(Severity.WARNING, "RAM usage", "could not check RAM usage"))

    try:
        uptime_days = get_uptime_days()
        if uptime_days <= 0:
            findings.append(_finding(Severity.WARNING, "System uptime", "could not check system uptime"))
        elif uptime_days > 30.0:
            findings.append(
                _finding(
                    Severity.WARNING,
                    "System uptime high",
                    f"System has been up for {uptime_days:.1f} days (warning threshold: >30 days).",
                )
            )
    except Exception:
        findings.append(_finding(Severity.WARNING, "System uptime", "could not check system uptime"))

    if pending_reboot():
        findings.append(
            _finding(
                Severity.WARNING,
                "Pending reboot",
                "A reboot is pending for Windows updates or servicing.",
            )
        )

    services = critical_services_stopped()
    if services:
        findings.append(
            _finding(
                Severity.WARNING,
                "Critical services stopped",
                f"Automatic services stopped: {', '.join(services)}.",
            )
        )

    if problem_devices_present():
        findings.append(
            _finding(
                Severity.WARNING,
                "Problem devices",
                "One or more devices are reporting configuration errors.",
            )
        )

    if physical_disk_unhealthy():
        findings.append(
            _finding(
                Severity.CRITICAL,
                "Physical disk health",
                "A physical disk reports a non-Healthy status.",
            )
        )

    if firewall_disabled():
        findings.append(
            _finding(
                Severity.WARNING,
                "Windows Firewall disabled",
                "At least one firewall profile is disabled.",
            )
        )

    if defender_realtime_off():
        findings.append(
            _finding(
                Severity.WARNING,
                "Windows Defender real-time protection",
                "Real-time protection is disabled.",
            )
        )

    if not findings:
        findings.append(
            _finding(
                Severity.OK,
                "No issues detected",
                "All health checks completed without warnings or critical findings.",
            )
        )

    return findings
