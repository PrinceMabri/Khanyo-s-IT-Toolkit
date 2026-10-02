"""Core helpers shared by every toolkit action.

Nothing in this module imports tkinter, so it is safe to use (and test) on
machines without a display.
"""

import ctypes
import getpass
import ipaddress
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from typing import List, Optional, Sequence, Union

from .config import IS_WINDOWS, REPORTS_DIR

Command = Union[str, Sequence[str]]

WINDOWS_ONLY = "Windows-only feature.\n"
NO_OUTPUT_PREFIX = "(command exited with code"

# Hostnames / IPs only. Must not start with "-" so a value can never be
# mistaken for a command-line option.
_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-:]*$")


# --------------------------------------------------------------------------
# Privileges
# --------------------------------------------------------------------------

def is_admin() -> bool:
    """Best-effort check for elevated (Administrator) privileges on Windows."""
    if not IS_WINDOWS:
        return False
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _relaunch_arguments() -> List[str]:
    """Work out how to start this same program again.

    Handles three cases: a frozen .exe (PyInstaller), `python -m package`,
    and a plain `python script.py`.
    """
    if getattr(sys, "frozen", False):
        return list(sys.argv[1:])
    spec = getattr(sys.modules.get("__main__"), "__spec__", None)
    if spec is not None and spec.name:
        module = spec.name
        if module.endswith(".__main__"):
            module = module[: -len(".__main__")]
        return ["-m", module] + list(sys.argv[1:])
    return list(sys.argv)


def relaunch_as_admin() -> bool:
    """Relaunch this program elevated. Returns True if Windows accepted the request."""
    if not IS_WINDOWS:
        return False
    try:
        params = subprocess.list2cmdline(_relaunch_arguments())
        # ShellExecuteW returns a value > 32 on success.
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        return result > 32
    except Exception:
        return False


# --------------------------------------------------------------------------
# Running commands
# --------------------------------------------------------------------------

def run_command(
    cmd: Command,
    shell: bool = False,
    timeout: int = 30,
    cancel_event: Optional[object] = None,
) -> str:
    """Run a command and return combined stdout/stderr as text.

    Never raises -- errors are captured and returned as text so the GUI
    thread can safely display them. Prefer passing `cmd` as a list.
    """
    if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
        return "Cancelled by user."

    try:
        if cancel_event is None:
            result = subprocess.run(
                cmd,
                shell=shell,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0,
            )
            output = result.stdout or ""
            if result.stderr:
                output += ("\n" if output else "") + result.stderr
            if not output.strip():
                output = f"{NO_OUTPUT_PREFIX} {result.returncode}, no output)"
            return output

        proc = subprocess.Popen(
            cmd,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0,
        )
        start = time.monotonic()
        stdout = ""
        stderr = ""
        while proc.poll() is None:
            if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return f"Cancelled by user.\n{stdout}\n{stderr}".strip()
            if timeout is not None and (time.monotonic() - start) > timeout:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return f"Command timed out after {timeout}s: {cmd}"
            time.sleep(0.1)

        stdout, stderr = proc.communicate()
        output = stdout or ""
        if stderr:
            output += ("\n" if output else "") + stderr
        if not output.strip():
            output = f"{NO_OUTPUT_PREFIX} {proc.returncode}, no output)"
        return output
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s: {cmd}"
    except FileNotFoundError:
        return f"Command not found: {cmd}\n(This tool is designed for Windows.)"
    except Exception as e:
        return f"Error running command: {e}"


def ps(command: str, timeout: int = 30) -> str:
    """Run a PowerShell script (passed as one string) and return its output."""
    return run_command(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        timeout=timeout,
    )


def has_output(text: str) -> bool:
    """True if `text` is real command output, not empty or the 'no output' placeholder."""
    stripped = text.strip()
    return bool(stripped) and not stripped.startswith(NO_OUTPUT_PREFIX)


def header(title: str) -> str:
    bar = "=" * 60
    return f"{bar}\n {title}\n{bar}\n"


def write_action_log(
    tool_label: str,
    success: bool,
    detail: str = "",
    *,
    report_dir: Optional[str] = None,
) -> str:
    """Append a single dangerous-action event to actions.log in the reports dir."""
    target_dir = report_dir or REPORTS_DIR
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, "actions.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = os.environ.get("USERNAME") or getpass.getuser()
    machine = socket.gethostname()
    status = "SUCCESS" if success else "ERROR"
    line = f"{timestamp}\t{username}\t{machine}\t{tool_label}\t{status}\t{detail or 'n/a'}\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line)
    return path


# --------------------------------------------------------------------------
# Input validation
# --------------------------------------------------------------------------

def is_safe_host(value: str) -> bool:
    """True if `value` looks like a plain hostname or IP address."""
    return bool(value) and len(value) <= 253 and bool(_HOST_RE.match(value))


def is_valid_ipv4(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value)
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------
# Small system metrics (used by the dashboard)
# --------------------------------------------------------------------------

def _last_float(text: str) -> Optional[float]:
    try:
        return float(text.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def get_memory_usage() -> Optional[float]:
    """Return memory usage percentage using Windows PowerShell, or None."""
    if not IS_WINDOWS:
        return None
    return _last_float(ps(
        "$os = Get-CimInstance Win32_OperatingSystem; "
        "[math]::Round((1 - ($os.FreePhysicalMemory / $os.TotalVisibleMemorySize)) * 100, 1)"
    ))


def get_cpu_usage() -> Optional[float]:
    """Return approximate current CPU usage percentage."""
    if not IS_WINDOWS:
        return None
    return _last_float(ps(
        "(Get-Counter '\\Processor(_Total)\\% Processor Time').CounterSamples.CookedValue"
    ))


def get_primary_drive_health() -> Optional[float]:
    """Return C: drive free-space percentage."""
    drive = "C:\\"
    if not os.path.exists(drive):
        return None
    try:
        total, _used, free = shutil.disk_usage(drive)
        return round((free / total) * 100, 1)
    except OSError:
        return None


def open_path(path: str) -> bool:
    """Open a file or folder with the default Windows handler. Returns success."""
    if not IS_WINDOWS:
        return False
    try:
        os.startfile(path)
        return True
    except OSError:
        return False
