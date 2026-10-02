import threading
from pathlib import Path

from khanyo_toolkit import core, findings
from khanyo_toolkit.actions import maintenance


def test_run_all_checks_reports_warning_and_critical(monkeypatch):
    monkeypatch.setattr(findings, "IS_WINDOWS", True)
    monkeypatch.setattr(findings, "get_cpu_usage", lambda: 95.0)
    monkeypatch.setattr(findings, "get_memory_usage", lambda: 92.0)
    monkeypatch.setattr(findings, "get_primary_drive_health", lambda: 7.0)
    monkeypatch.setattr(findings, "get_uptime_days", lambda: 33.0)
    monkeypatch.setattr(findings, "pending_reboot", lambda: True)
    monkeypatch.setattr(findings, "critical_services_stopped", lambda: ["Dnscache", "Winmgmt"])
    monkeypatch.setattr(findings, "problem_devices_present", lambda: True)
    monkeypatch.setattr(findings, "physical_disk_unhealthy", lambda: True)
    monkeypatch.setattr(findings, "firewall_disabled", lambda: True)
    monkeypatch.setattr(findings, "defender_realtime_off", lambda: True)

    items = findings.run_all_checks()
    assert any(item.severity.name == "CRITICAL" for item in items)
    assert any("RAM" in item.title or "free space" in item.title for item in items)
    assert any(item.source_tool == "system" for item in items)


def test_write_action_log_appends_entry(tmp_path):
    log_path = core.write_action_log(
        "Clean Temp Files",
        True,
        "completed",
        report_dir=str(tmp_path),
    )
    assert Path(log_path).exists()
    text = Path(log_path).read_text(encoding="utf-8")
    assert "Clean Temp Files" in text
    assert "SUCCESS" in text


def test_run_command_cancel_event_stops_immediately():
    cancel = threading.Event()
    cancel.set()
    out = core.run_command(["python", "-c", "import time; time.sleep(10)"], cancel_event=cancel)
    assert "Cancelled" in out


def test_clean_temp_files_dry_run_and_real_delete(monkeypatch, tmp_path):
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    (temp_dir / "old.txt").write_bytes(b"1234567890")
    monkeypatch.setenv("TEMP", str(temp_dir))

    dry_run = maintenance.action_clean_temp_files(dry_run=True)
    assert "Dry run" in dry_run
    assert (temp_dir / "old.txt").exists()

    real = maintenance.action_clean_temp_files(confirm=True)
    assert "deleted" in real.lower()
    assert not (temp_dir / "old.txt").exists()
