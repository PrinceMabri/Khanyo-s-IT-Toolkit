"""The tool registry: every action the toolkit offers, grouped by GUI tab.

To add a tool, write an action function in `actions/` and add one `Tool(...)`
line to the right category below. See docs/ADDING_TOOLS.md.
"""

from typing import Callable, Dict, List, NamedTuple

from .actions import maintenance, network, system


class Tool(NamedTuple):
    label: str
    func: Callable[[], str]
    tooltip: str
    dangerous: bool = False  # True = changes system state; excluded from auto reports


CATEGORIES: Dict[str, List[Tool]] = {
    "Dashboard": [
        Tool("Health Snapshot", system.action_health_snapshot,
             "Quick read-only CPU, memory, disk and privilege overview"),
    ],
    "System": [
        Tool("System Information", system.action_system_info, "Detailed OS, hardware & hotfix info"),
        Tool("Hardware Inventory", system.action_hardware_inventory, "CPU, RAM, GPU and physical disk inventory"),
        Tool("Disk Health", system.action_disk_health, "Physical disk health and logical disk space"),
        Tool("Battery Status", system.action_battery_status, "Current battery status for laptops"),
        Tool("System Uptime", system.action_system_uptime, "How long since the last reboot"),
        Tool("Startup Programs", system.action_startup_programs, "Apps that launch at sign-in"),
        Tool("Running Processes", system.action_running_processes, "Currently running tasks"),
        Tool("Disk Space", system.action_disk_space, "Free / used space per drive"),
        Tool("Installed Programs", system.action_installed_programs, "List of installed software"),
        Tool("Windows Update Check", system.action_windows_update_check, "Recent updates & pending reboot"),
        Tool("Important Services", system.action_services_overview, "Check key Windows services"),
        Tool("Problem Devices", system.action_device_manager_summary, "Find Windows device configuration errors"),
        Tool("Recent System Errors", system.action_windows_event_errors, "Show recent System event errors"),
    ],
    "Network": [
        Tool("IP Configuration", network.action_ip_config, "Adapter IPs, DNS servers, MAC address"),
        Tool("Wi-Fi Status", network.action_wifi_status, "Current wireless connection details"),
        Tool("Network Adapters", network.action_ethernet_adapters, "Ethernet and Wi-Fi adapter status"),
        Tool("Gateway & DNS Diagnostics", network.action_gateway_dns_diagnostics,
             "Gateway reachability and DNS diagnostics"),
        Tool("Ping Test", network.action_ping_test, "Ping 8.8.8.8 to check connectivity"),
        Tool("DNS Test", network.action_dns_test, "Resolve google.com"),
        Tool("Network Test", network.action_network_test, "Gateway, DNS servers & public IP"),
        Tool("Traceroute", network.action_traceroute, "Trace the route to 8.8.8.8"),
        Tool("Port Test", network.action_port_test, "Test common TCP connectivity"),
        Tool("Active Connections", network.action_active_connections, "Open ports & live connections"),
        Tool("Firewall Status", network.action_firewall_status, "Windows Firewall profile status"),
        Tool("Clear DNS Cache", network.action_clear_dns_cache, "Flush the local DNS resolver cache", True),
        Tool("Reset Network Adapter", network.action_reset_network_adapter,
             "Release/renew IP + reset Winsock/TCP", True),
    ],
    "Maintenance": [
        Tool("Restart Print Spooler", maintenance.action_restart_print_spooler, "Fixes stuck print jobs", True),
        Tool("Clean Temp Files", maintenance.action_clean_temp_files, "Deletes files in %TEMP%", True),
        Tool("Empty Recycle Bin", maintenance.action_empty_recycle_bin, "Clears the Recycle Bin", True),
        Tool("Create Restore Point", maintenance.action_create_restore_point,
             "New System Protection checkpoint", True),
        Tool("Quick Health Scan", maintenance.action_quick_health_scan, "DISM + SFC verify-only scan", True),
        Tool("Battery Report", maintenance.action_battery_report, "Battery health report (laptops)", True),
    ],
}

# Safe, read-only tools bundled into the automatic Support Report.
REPORT_TOOLS: List[Tool] = [t for tools in CATEGORIES.values() for t in tools if not t.dangerous]
