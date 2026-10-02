"""Maintenance actions. These change system state, so the GUI marks them as
'dangerous' and the automatic support report never runs them."""

import os

from ..config import IS_WINDOWS
from ..core import WINDOWS_ONLY, header, is_admin, open_path, ps, run_command


def _temp_file_plan(temp_dir: str):
    files = []
    total_size = 0
    for root, _dirs, filenames in os.walk(temp_dir):
        for name in filenames:
            path = os.path.join(root, name)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            files.append((path, size))
            total_size += size
    return files, total_size


def action_restart_print_spooler(cancel_event=None) -> str:
    out = header("RESTART PRINT SPOOLER SERVICE")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    if not is_admin():
        out += "WARNING: Not running as Administrator. This will likely fail.\n\n"
    out += "--- Stopping spooler ---\n" + run_command(["net", "stop", "spooler"], cancel_event=cancel_event)
    out += "\n--- Starting spooler ---\n" + run_command(["net", "start", "spooler"], cancel_event=cancel_event)
    return out


def action_clean_temp_files(dry_run: bool = False, confirm: bool = False) -> str:
    out = header("CLEAN TEMP FILES")
    temp_dir = os.environ.get("TEMP") or os.environ.get("TMP")
    if not temp_dir or not os.path.isdir(temp_dir):
        return out + "Could not locate a TEMP directory.\n"

    files, total_size = _temp_file_plan(temp_dir)
    preview_text = (
        f"Dry run: {len(files)} file(s) and {total_size / (1024 ** 2):.1f} "
        "MB would be deleted."
    )
    if dry_run:
        out += f"Temp folder:  {temp_dir}\n"
        out += f"{preview_text}\n"
        return out
    if not confirm:
        out += f"Temp folder:  {temp_dir}\n"
        out += f"{preview_text}\n"
        out += "Confirmation required before deleting. Re-run with confirm=True.\n"
        return out

    freed, deleted, errors = 0, 0, 0
    for path, size in files:
        try:
            os.remove(path)
            freed += size
            deleted += 1
        except Exception:
            errors += 1
    out += f"Temp folder:  {temp_dir}\n"
    out += f"Files deleted: {deleted}\n"
    out += f"Space freed:   {freed / (1024 ** 2):.1f} MB\n"
    out += f"Skipped (in use / locked): {errors}\n"
    return out


def action_empty_recycle_bin() -> str:
    out = header("EMPTY RECYCLE BIN")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    out += ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
    out += "Recycle Bin emptied (if it contained items).\n"
    return out


def action_create_restore_point() -> str:
    out = header("CREATE SYSTEM RESTORE POINT")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    if not is_admin():
        out += "WARNING: Requires Administrator privileges.\n\n"
    out += ps(
        "Checkpoint-Computer -Description 'Khanyo IT Toolkit' -RestorePointType MODIFY_SETTINGS",
        timeout=60,
    )
    out += "\nNote: Windows only allows one System Protection checkpoint every 24 hours by default.\n"
    return out


def action_quick_health_scan(cancel_event=None) -> str:
    out = header("QUICK SYSTEM HEALTH SCAN (DISM + SFC verify)")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    if not is_admin():
        out += "WARNING: Requires Administrator privileges for accurate results.\n\n"
    out += "--- DISM image health check ---\n"
    out += run_command(
        ["DISM", "/Online", "/Cleanup-Image", "/CheckHealth"],
        timeout=60,
        cancel_event=cancel_event,
    ) + "\n"
    out += "--- SFC verify-only (can take a few minutes) ---\n"
    out += run_command(
        ["sfc", "/verifyonly"],
        timeout=300,
        cancel_event=cancel_event,
    ) + "\n"
    return out


def action_battery_report() -> str:
    out = header("BATTERY REPORT")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    report_path = os.path.join(os.environ.get("TEMP", "."), "khanyo_battery_report.html")
    out += run_command(["powercfg", "/batteryreport", "/output", report_path]) + "\n"
    if os.path.exists(report_path):
        out += f"Report saved to: {report_path}\n"
        if open_path(report_path):
            out += "Opened in default browser.\n"
    else:
        out += "No battery detected (likely a desktop PC), or report generation failed.\n"
    return out
