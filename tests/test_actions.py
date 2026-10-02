"""Action tests. Commands are mocked so these run on any OS."""

from khanyo_toolkit.actions import maintenance, network, system
from khanyo_toolkit.core import WINDOWS_ONLY


def test_windows_only_actions_degrade_gracefully(monkeypatch):
    monkeypatch.setattr(system, "IS_WINDOWS", False)
    monkeypatch.setattr(network, "IS_WINDOWS", False)
    monkeypatch.setattr(maintenance, "IS_WINDOWS", False)
    for func in [
        system.action_startup_programs, system.action_disk_health, system.action_battery_status,
        system.action_installed_programs, system.action_windows_update_check,
        system.action_services_overview, system.action_device_manager_summary,
        system.action_windows_event_errors, network.action_wifi_status,
        network.action_ethernet_adapters, network.action_firewall_status,
        network.action_clear_dns_cache, network.action_reset_network_adapter,
        maintenance.action_restart_print_spooler, maintenance.action_empty_recycle_bin,
        maintenance.action_create_restore_point, maintenance.action_quick_health_scan,
        maintenance.action_battery_report,
    ]:
        assert WINDOWS_ONLY.strip() in func(), func.__name__


def test_health_snapshot_uses_real_newlines(monkeypatch):
    # Regression: v1.2 emitted a literal backslash-n instead of a newline.
    monkeypatch.setattr(system, "get_cpu_usage", lambda: 12.34)
    monkeypatch.setattr(system, "get_memory_usage", lambda: None)
    monkeypatch.setattr(system, "get_primary_drive_health", lambda: 55.0)
    out = system.action_health_snapshot()
    assert "\\n" not in out
    assert "CPU Usage:       12.3%" in out
    assert "Memory Usage:    unavailable" in out
    assert out.count("\n") >= 8


def test_device_manager_reports_no_problems_when_empty(monkeypatch):
    # Regression: v1.2 never reached the "no problem devices" message.
    monkeypatch.setattr(system, "IS_WINDOWS", True)
    monkeypatch.setattr(system, "ps", lambda *a, **k: "(command exited with code 0, no output)")
    assert "No problem devices detected" in system.action_device_manager_summary()


def test_device_manager_shows_results_when_present(monkeypatch):
    monkeypatch.setattr(system, "IS_WINDOWS", True)
    monkeypatch.setattr(system, "ps", lambda *a, **k: "Name  Status\nBad Device  Error")
    out = system.action_device_manager_summary()
    assert "Bad Device" in out and "No problem devices" not in out


def test_battery_status_detects_desktop(monkeypatch):
    monkeypatch.setattr(system, "IS_WINDOWS", True)
    monkeypatch.setattr(system, "ps", lambda *a, **k: "(command exited with code 0, no output)")
    assert "No battery detected" in system.action_battery_status()


def test_ping_rejects_unsafe_target(monkeypatch):
    called = []
    monkeypatch.setattr(network, "run_command", lambda *a, **k: called.append(a) or "")
    out = network.action_ping_test("8.8.8.8 & calc")
    assert "Invalid target" in out
    assert not called


def test_dns_rejects_option_like_domain(monkeypatch):
    called = []
    monkeypatch.setattr(network, "run_command", lambda *a, **k: called.append(a) or "")
    assert "Invalid domain" in network.action_dns_test("-debug")
    assert not called


def test_default_gateway_parsing(monkeypatch):
    monkeypatch.setattr(network, "IS_WINDOWS", True)
    monkeypatch.setattr(network, "ps", lambda *a, **k: "192.168.1.1\n")
    assert network.get_default_gateway() == "192.168.1.1"
    monkeypatch.setattr(network, "ps", lambda *a, **k: "(command exited with code 0, no output)")
    assert network.get_default_gateway() is None


def test_disk_space_runs_everywhere():
    assert "DISK SPACE" in system.action_disk_space()
