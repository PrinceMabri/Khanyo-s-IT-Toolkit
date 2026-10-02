from khanyo_toolkit import reports
from khanyo_toolkit.registry import Tool


def test_collect_sections_survives_a_failing_tool():
    def boom():
        raise RuntimeError("kaboom")

    tools = [Tool("Good", lambda: "ok", "tip"), Tool("Bad", boom, "tip")]
    seen = []
    sections = reports.collect_sections(tools, progress=seen.append)
    assert seen == ["Good", "Bad"]
    assert sections[0] == ("Good", "ok")
    assert sections[1][0] == "Bad" and "kaboom" in sections[1][1]


def test_render_txt_contains_all_sections():
    text = reports.render_txt([("A", "alpha output"), ("B", "beta output")])
    assert "SUPPORT REPORT" in text
    assert "alpha output" in text and "beta output" in text


def test_render_html_escapes_content():
    page = reports.render_html([("<b>x</b>", "<script>alert(1)</script>")])
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
    assert page.lstrip().startswith("<!DOCTYPE html>")


def test_render_dispatch():
    sections = [("A", "x")]
    assert "<html" in reports.render(sections, "html")
    assert "<html" not in reports.render(sections, "txt")


def test_default_report_name():
    name = reports.default_report_name("html")
    assert name.startswith("khanyo_support_report_") and name.endswith(".html")


def test_write_report_creates_missing_folders(tmp_path):
    target = tmp_path / "nested" / "dir" / "r.txt"
    reports.write_report(str(target), "hello")
    assert target.read_text(encoding="utf-8") == "hello"


def test_redact_text_masks_identity_data():
    text = (
        "Host: PC-01\n"
        "IPv4: 192.168.0.10\n"
        "MAC: 00-11-22-33-44-55\n"
        "User: alice\n"
        "UserName: alice@example.com\n"
    )
    redacted = reports.redact_text(text)
    assert "PC-01" not in redacted
    assert "192.168.0.10" not in redacted
    assert "00-11-22-33-44-55" not in redacted
    assert "alice" not in redacted.lower()


def test_render_txt_includes_ticket_metadata():
    text = reports.render_txt(
        [("A", "alpha output")],
        findings=[],
        client="Acme Corp",
        ticket="T-42",
        technician="Sam",
        notes="Customer needs follow-up",
    )
    assert "Acme Corp" in text
    assert "T-42" in text
    assert "Sam" in text
    assert "Customer needs follow-up" in text
