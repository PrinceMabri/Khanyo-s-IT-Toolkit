import pytest

import khanyo_toolkit.app as app_module
from khanyo_toolkit import __version__, cli
from khanyo_toolkit.registry import Tool


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_list_tools(capsys):
    assert cli.main(["--list-tools"]) == 0
    out = capsys.readouterr().out
    assert "[Network]" in out and "Ping Test" in out and "changes system state" in out


def test_output_requires_report():
    with pytest.raises(SystemExit):
        cli.main(["-o", "x.txt"])


def test_headless_report(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "REPORT_TOOLS", [Tool("Demo", lambda: "demo output", "tip")])
    target = tmp_path / "out" / "r.html"
    assert cli.main(["--report", "html", "-o", str(target)]) == 0
    text = target.read_text(encoding="utf-8")
    assert "demo output" in text and "<html" in text


def test_headless_report_json_includes_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "REPORT_TOOLS", [Tool("Demo", lambda: "demo output", "tip")])
    target = tmp_path / "out" / "r.json"
    assert cli.main([
        "--report", "json",
        "-o", str(target),
        "--client", "Acme Corp",
        "--ticket", "T-42",
        "--technician", "Sam",
        "--notes", "Customer follow-up",
    ]) == 0
    payload = target.read_text(encoding="utf-8")
    assert "Acme Corp" in payload and "T-42" in payload and "Customer follow-up" in payload


def test_list_recent_reports(tmp_path, monkeypatch, capsys):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "older.txt").write_text("old", encoding="utf-8")
    (report_dir / "newer.html").write_text("new", encoding="utf-8")
    monkeypatch.setattr(cli, "REPORTS_DIR", str(report_dir))
    monkeypatch.setattr(cli, "IS_WINDOWS", False)
    assert cli.main(["--report-history"]) == 0
    captured = capsys.readouterr()
    assert "newer.html" in captured.out and "older.txt" in captured.out


def test_open_last_report(tmp_path, monkeypatch, capsys):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    target = report_dir / "latest.html"
    target.write_text("new", encoding="utf-8")
    monkeypatch.setattr(cli, "REPORTS_DIR", str(report_dir))
    monkeypatch.setattr(cli, "IS_WINDOWS", True)
    monkeypatch.setattr(cli, "open_path", lambda path: (print(path), True)[1])
    assert cli.main(["--open-last-report"]) == 0
    captured = capsys.readouterr()
    assert "latest.html" in captured.out


def test_reports_tab_uses_tk_checkbutton(monkeypatch):
    class DummyVar:
        def __init__(self, value=None):
            self.value = value

    class DummyWidget:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def pack(self, *args, **kwargs):
            return None

    class DummyNotebook:
        def add(self, *args, **kwargs):
            return None

    monkeypatch.setattr(app_module.tk, "StringVar", DummyVar)
    monkeypatch.setattr(app_module.tk, "BooleanVar", DummyVar)
    monkeypatch.setattr(app_module.tk, "Checkbutton", lambda *args, **kwargs: DummyWidget(*args, **kwargs))
    monkeypatch.setattr(app_module.ttk, "Checkbutton", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ttk.Checkbutton should not be used here")))
    monkeypatch.setattr(app_module.ttk, "Frame", lambda *args, **kwargs: DummyWidget(*args, **kwargs))
    monkeypatch.setattr(app_module.ttk, "Label", lambda *args, **kwargs: DummyWidget(*args, **kwargs))
    monkeypatch.setattr(app_module.ttk, "Entry", lambda *args, **kwargs: DummyWidget(*args, **kwargs))
    monkeypatch.setattr(app_module.ttk, "Button", lambda *args, **kwargs: DummyWidget(*args, **kwargs))

    app = object.__new__(app_module.KhanyoApp)
    app.notebook = DummyNotebook()
    app.TEXT_FG = "#e6e9ef"
    app.PANEL = "#1f2430"

    app._build_reports_tab()


def test_report_history_supports_limit(tmp_path, monkeypatch, capsys):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "older.txt").write_text("old", encoding="utf-8")
    (report_dir / "newer.html").write_text("new", encoding="utf-8")
    monkeypatch.setattr(cli, "REPORTS_DIR", str(report_dir))
    assert cli.main(["--report-history", "--limit", "1"]) == 0
    captured = capsys.readouterr()
    assert "newer.html" in captured.out
    assert "older.txt" not in captured.out
