"""Network diagnostics and network repair actions."""

import urllib.request
from typing import Optional

from ..config import IS_WINDOWS
from ..core import (
    WINDOWS_ONLY,
    header,
    is_admin,
    is_safe_host,
    is_valid_ipv4,
    ps,
    run_command,
)


def _ping_cmd(target: str, count: int):
    return ["ping", "-n" if IS_WINDOWS else "-c", str(count), target]


def get_default_gateway() -> Optional[str]:
    """Return the IPv4 default gateway (Windows only), or None."""
    if not IS_WINDOWS:
        return None
    raw = ps(
        "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | "
        "Sort-Object RouteMetric | Select-Object -First 1).NextHop"
    ).strip()
    first = raw.splitlines()[0].strip() if raw else ""
    return first if is_valid_ipv4(first) else None


def action_ip_config() -> str:
    out = header("IP CONFIGURATION")
    if IS_WINDOWS:
        out += run_command(["ipconfig", "/all"])
    else:
        out += run_command("ip addr || ifconfig -a", shell=True)
    return out


def action_wifi_status() -> str:
    out = header("WI-FI STATUS")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    out += run_command(["netsh", "wlan", "show", "interfaces"])
    return out


def action_ethernet_adapters() -> str:
    out = header("NETWORK ADAPTER STATUS")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    out += ps(
        "Get-NetAdapter | "
        "Select-Object Name, InterfaceDescription, Status, LinkSpeed, MacAddress | "
        "Format-Table -AutoSize"
    )
    return out


def action_gateway_dns_diagnostics() -> str:
    out = header("GATEWAY & DNS DIAGNOSTICS")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY

    gateway = get_default_gateway()
    out += f"Default Gateway: {gateway or 'Not detected'}\n\n"

    if gateway:
        out += f"--- Gateway Ping ({gateway}) ---\n"
        out += run_command(_ping_cmd(gateway, 4)) + "\n"
    else:
        out += "--- Gateway Ping ---\nNo IPv4 gateway detected.\n\n"

    out += "--- DNS Configuration ---\n"
    out += ps(
        "Get-DnsClientServerAddress -AddressFamily IPv4 | "
        "Where-Object {$_.ServerAddresses} | "
        "Select-Object InterfaceAlias, ServerAddresses | "
        "Format-Table -AutoSize"
    )
    out += "\n--- DNS Resolution ---\n"
    out += run_command(["nslookup", "google.com"])
    return out


def action_ping_test(target: str = "8.8.8.8") -> str:
    out = header(f"PING TEST -> {target}")
    if not is_safe_host(target):
        return out + "Invalid target: only hostnames and IP addresses are allowed.\n"
    out += run_command(_ping_cmd(target, 4))
    return out


def action_dns_test(domain: str = "google.com") -> str:
    out = header(f"DNS TEST -> {domain}")
    if not is_safe_host(domain):
        return out + "Invalid domain: only hostnames are allowed.\n"
    out += run_command(["nslookup", domain])
    return out


def action_network_test() -> str:
    out = header("NETWORK TEST")
    if IS_WINDOWS:
        gateway = get_default_gateway()
        out += f"--- Default gateway ---\n{gateway or 'Not detected'}\n"
        if gateway:
            out += f"--- Ping gateway ({gateway}) ---\n"
            out += run_command(_ping_cmd(gateway, 2)) + "\n"

    for label, tgt in [("Google DNS (8.8.8.8)", "8.8.8.8"), ("Cloudflare DNS (1.1.1.1)", "1.1.1.1")]:
        out += f"--- Ping {label} ---\n"
        out += run_command(_ping_cmd(tgt, 2)) + "\n"

    out += "--- Public IP lookup ---\n"
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
            out += "Public IP: " + resp.read().decode().strip() + "\n"
    except Exception as e:
        out += f"Could not reach public IP lookup service: {e}\n"
    return out


def action_traceroute(cancel_event=None) -> str:
    out = header("TRACEROUTE TO 8.8.8.8")
    cmd = ["tracert", "-d", "-h", "12", "8.8.8.8"] if IS_WINDOWS else ["traceroute", "-n", "-m", "12", "8.8.8.8"]
    out += run_command(cmd, timeout=45, cancel_event=cancel_event)
    return out


def action_port_test() -> str:
    out = header("COMMON PORT TEST")
    if not IS_WINDOWS:
        out += "Windows-focused feature.\n"
        return out

    out += "Testing Google DNS TCP ports 53 and HTTPS port 443.\n\n"
    out += "--- TCP 53 ---\n"
    out += ps(
        "$r = Test-NetConnection 8.8.8.8 -Port 53 -WarningAction SilentlyContinue; "
        "'RemotePort: ' + $r.RemotePort; "
        "'TcpTestSucceeded: ' + $r.TcpTestSucceeded"
    )
    out += "\n--- TCP 443 ---\n"
    out += ps(
        "$r = Test-NetConnection google.com -Port 443 -WarningAction SilentlyContinue; "
        "'RemotePort: ' + $r.RemotePort; "
        "'TcpTestSucceeded: ' + $r.TcpTestSucceeded"
    )
    return out


def action_active_connections() -> str:
    out = header("ACTIVE NETWORK CONNECTIONS")
    out += run_command(["netstat", "-ano"] if IS_WINDOWS else ["netstat", "-tunap"], timeout=20)
    return out


def action_firewall_status() -> str:
    out = header("FIREWALL STATUS")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    out += run_command(["netsh", "advfirewall", "show", "allprofiles"])
    return out


# ---- state-changing actions ------------------------------------------------

def action_clear_dns_cache() -> str:
    out = header("CLEAR DNS CACHE")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    if not is_admin():
        out += "WARNING: Not running as Administrator. This may fail.\n\n"
    out += run_command(["ipconfig", "/flushdns"])
    return out


def action_reset_network_adapter(cancel_event=None) -> str:
    out = header("RESET NETWORK ADAPTER")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    if not is_admin():
        out += "WARNING: Requires Administrator privileges. Relaunch as admin and try again.\n\n"
    out += "--- Releasing IP ---\n"
    out += run_command(["ipconfig", "/release"], cancel_event=cancel_event) + "\n"
    out += "--- Renewing IP ---\n"
    out += run_command(["ipconfig", "/renew"], cancel_event=cancel_event) + "\n"
    out += "--- Resetting Winsock catalog ---\n"
    out += run_command(["netsh", "winsock", "reset"], cancel_event=cancel_event) + "\n"
    out += "--- Resetting TCP/IP stack ---\n"
    out += run_command(["netsh", "int", "ip", "reset"], cancel_event=cancel_event) + "\n"
    out += "\nNOTE: A restart is recommended for the Winsock/TCP reset to fully take effect.\n"
    return out
