import sys

from khanyo_toolkit import core


def test_header_contains_title():
    out = core.header("HELLO")
    assert "HELLO" in out
    assert out.startswith("=" * 60)


def test_run_command_captures_output():
    out = core.run_command([sys.executable, "-c", "print('hi')"])
    assert "hi" in out


def test_run_command_empty_output_placeholder():
    out = core.run_command([sys.executable, "-c", "pass"])
    assert out.startswith(core.NO_OUTPUT_PREFIX)
    assert not core.has_output(out)


def test_run_command_missing_program_does_not_raise():
    out = core.run_command(["definitely-not-a-real-program-xyz"])
    assert "not found" in out.lower()


def test_run_command_timeout_does_not_raise():
    out = core.run_command([sys.executable, "-c", "import time; time.sleep(5)"], timeout=1)
    assert "timed out" in out


def test_has_output():
    assert core.has_output("some text")
    assert not core.has_output("   \n")
    assert not core.has_output("(command exited with code 0, no output)")


def test_is_safe_host_accepts_normal_values():
    for value in ["8.8.8.8", "google.com", "my-host.local", "2001:db8::1"]:
        assert core.is_safe_host(value), value


def test_is_safe_host_rejects_injection_and_options():
    for value in ["", "-n 100", "8.8.8.8 & calc", "a;b", "x|y", "$(whoami)", "a b", "a" * 300]:
        assert not core.is_safe_host(value), value


def test_is_valid_ipv4():
    assert core.is_valid_ipv4("192.168.0.1")
    assert not core.is_valid_ipv4("999.1.1.1")
    assert not core.is_valid_ipv4("not-an-ip")
    assert not core.is_valid_ipv4("")


def test_last_float_parsing():
    assert core._last_float("noise\n42.5\n") == 42.5
    assert core._last_float("") is None
    assert core._last_float("abc") is None
