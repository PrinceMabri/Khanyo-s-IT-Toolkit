"""System diagnostics: OS, hardware, disks, services and event logs."""

import os
import platform
import shutil
import socket
import string

from ..config import IS_WINDOWS
from ..core import (
    WINDOWS_ONLY,
    get_cpu_usage,
    get_memory_usage,
    get_primary_drive_health,
    has_output,
    header,
    is_admin,
    ps,
    run_command,
)


def action_health_snapshot() -> str:
    """Compact read-only snapshot used by the dashboard."""
    out = header("KHANYO HEALTH SNAPSHOT")

    def fmt(value):
        return "unavailable" if value is None else f"{value:.1f}%"

    out += f"CPU Usage:       {fmt(get_cpu_usage())}\n"
    out += f"Memory Usage:    {fmt(get_memory_usage())}\n"
    out += f"C: Drive Free:   {fmt(get_primary_drive_health())}\n"
    out += f"Administrator:   {is_admin()}\n"
    out += f"Hostname:        {socket.gethostname()}\n"
    return out


def action_system_info() -> str:
    out = header("SYSTEM INFORMATION")
    out += f"Hostname:         {socket.gethostname()}\n"
    out += f"OS:               {platform.platform()}\n"
    out += f"Processor:        {platform.processor()}\n"
    out += f"Python:           {platform.python_version()}\n"
    out += f"Running as Admin: {is_admin()}\n\n"
    if IS_WINDOWS:
        out += "--- systeminfo (detailed) ---\n"
        out += run_command(["systeminfo"], timeout=45)
    return out


def action_hardware_inventory() -> str:
    out = header("HARDWARE INVENTORY")
    if not IS_WINDOWS:
        out += "Windows-only hardware inventory.\n"
        return out

    out += "--- CPU ---\n"
    out += ps(
        "Get-CimInstance Win32_Processor | "
        "Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed | "
        "Format-List"
    )
    out += "\n--- Memory Modules ---\n"
    out += ps(
        "Get-CimInstance Win32_PhysicalMemory | "
        "Select-Object Manufacturer, PartNumber, @{N='CapacityGB';E={[math]::Round($_.Capacity/1GB,2)}}, Speed | "
        "Format-Table -AutoSize"
    )
    out += "\n--- GPU ---\n"
    out += ps(
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name, DriverVersion, "
        "@{N='AdapterRAMGB';E={if($_.AdapterRAM){[math]::Round($_.AdapterRAM/1GB,2)}else{'N/A'}}} | "
        "Format-Table -AutoSize"
    )
    out += "\n--- Physical Disks ---\n"
    out += ps(
        "Get-CimInstance Win32_DiskDrive | "
        "Select-Object Model, InterfaceType, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}, Status | "
        "Format-Table -AutoSize"
    )
    return out


def action_system_uptime() -> str:
    out = header("SYSTEM UPTIME")
    if IS_WINDOWS:
        out += ps(
            "$os = Get-CimInstance Win32_OperatingSystem; "
            "$up = (Get-Date) - $os.LastBootUpTime; "
            "'Last Boot Time: ' + $os.LastBootUpTime; "
            "'Uptime: ' + $up.Days + ' days, ' + $up.Hours + ' hours, ' + $up.Minutes + ' minutes'"
        )
    else:
        out += run_command(["uptime"])
    return out


def action_startup_programs() -> str:
    out = header("STARTUP PROGRAMS")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    out += ps(
        "Get-CimInstance Win32_StartupCommand | "
        "Select-Object Name, Command, Location, User | Format-Table -AutoSize"
    )
    return out


def action_running_processes() -> str:
    out = header("RUNNING PROCESSES")
    out += run_command(["tasklist"] if IS_WINDOWS else ["ps", "aux"])
    return out


def action_disk_space() -> str:
    out = header("DISK SPACE")
    if IS_WINDOWS:
        # `wmic` was removed from recent Windows 11 builds, so use CIM instead.
        out += ps(
            "Get-CimInstance Win32_LogicalDisk | "
            "Select-Object DeviceID, VolumeName, FileSystem, "
            "@{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}, "
            "@{N='FreeGB';E={[math]::Round($_.FreeSpace/1GB,2)}} | "
            "Format-Table -AutoSize"
        )
        out += "\n--- Friendly summary ---\n"
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            try:
                total, used, free = shutil.disk_usage(drive)
                gb = 1024 ** 3
                out += (
                    f"{drive}  Total: {total / gb:6.1f} GB   "
                    f"Used: {used / gb:6.1f} GB   Free: {free / gb:6.1f} GB   "
                    f"({free / total * 100:.1f}% free)\n"
                )
            except Exception:
                pass
    return out


def action_disk_health() -> str:
    out = header("DISK HEALTH")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY

    out += "--- Physical Disk Status ---\n"
    out += ps(
        "Get-PhysicalDisk -ErrorAction SilentlyContinue | "
        "Select-Object FriendlyName, MediaType, HealthStatus, OperationalStatus, "
        "@{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}} | "
        "Format-Table -AutoSize"
    )
    out += "\n--- Logical Disk Space ---\n"
    out += action_disk_space()
    return out


def action_battery_status() -> str:
    out = header("BATTERY STATUS")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY

    result = ps(
        "Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | "
        "Select-Object Name, Status, EstimatedChargeRemaining, BatteryStatus | "
        "Format-Table -AutoSize"
    )
    if has_output(result):
        out += result.strip() + "\n"
    else:
        out += "No battery detected. This may be a desktop PC.\n"
    return out


def action_installed_programs() -> str:
    out = header("INSTALLED PROGRAMS")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    out += ps(
        "Get-ItemProperty "
        "HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, "
        "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* "
        "-ErrorAction SilentlyContinue | Where-Object { $_.DisplayName } | "
        "Select-Object DisplayName, DisplayVersion, Publisher | "
        "Sort-Object DisplayName | Format-Table -AutoSize",
    )
    return out


def action_windows_update_check() -> str:
    out = header("WINDOWS UPDATE CHECK")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    out += "--- Recently installed updates (last 10) ---\n"
    out += ps(
        "Get-HotFix | Sort-Object InstalledOn -Descending | "
        "Select-Object -First 10 HotFixID, Description, InstalledOn | Format-Table -AutoSize",
        timeout=45,
    )
    out += "\n--- Pending reboot check ---\n"
    out += ps(
        "if (Test-Path "
        "'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired') "
        "{ 'Reboot REQUIRED' } else { 'No reboot pending' }"
    )
    out += (
        "\nNote: For a full scan against Microsoft's update servers, use "
        "Settings > Windows Update, or the PSWindowsUpdate module if installed.\n"
    )
    return out


def action_services_overview() -> str:
    out = header("IMPORTANT WINDOWS SERVICES")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY

    names = ["Dhcp", "Dnscache", "Spooler", "wuauserv", "BITS", "Winmgmt", "EventLog", "LanmanWorkstation"]
    joined = ",".join(f"'{n}'" for n in names)
    out += ps(
        f"Get-Service -Name {joined} -ErrorAction SilentlyContinue | "
        "Select-Object Name, DisplayName, Status, StartType | "
        "Format-Table -AutoSize"
    )
    return out


def action_device_manager_summary() -> str:
    out = header("DEVICE MANAGER -- PROBLEM DEVICES")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY

    result = ps(
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object {$_.ConfigManagerErrorCode -and $_.ConfigManagerErrorCode -ne 0} | "
        "Select-Object Name, Status, ConfigManagerErrorCode, PNPClass | "
        "Format-Table -AutoSize"
    )
    if has_output(result):
        out += result
    else:
        out += "No problem devices detected by this query.\n"
    return out


def action_windows_event_errors() -> str:
    out = header("RECENT WINDOWS SYSTEM ERRORS")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY

    out += ps(
        "Get-WinEvent -FilterHashtable @{LogName='System'; Level=2} -MaxEvents 20 "
        "-ErrorAction SilentlyContinue | "
        "Select-Object TimeCreated, ProviderName, Id, "
        "@{N='Message';E={$_.Message -replace '\\r?\\n',' '}} | "
        "Format-List",
        timeout=45,
    )
    return out
