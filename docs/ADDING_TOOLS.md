# Adding a new tool

A tool is a function that takes no arguments and returns a string.

## 1. Write the action

Put it in the module that fits: `actions/system.py`, `actions/network.py` or `actions/maintenance.py`.

```python
def action_list_shares() -> str:
    out = header("NETWORK SHARES")
    if not IS_WINDOWS:
        return out + WINDOWS_ONLY
    out += run_command(["net", "share"])
    return out
```

Helpers from `khanyo_toolkit.core`:

| Helper | Use |
| --- | --- |
| `run_command(list_or_str, timeout=30)` | Run a program; never raises, returns text |
| `ps("PowerShell script")` | Run PowerShell and return its output |
| `header("TITLE")` | Consistent section banner |
| `has_output(text)` | `False` for empty / "no output" results |
| `is_admin()` | Check for elevation |
| `is_safe_host(value)` | Validate hostnames / IPs before using them in a command |

## 2. Register it

Add one line to the right category in `registry.py`:

```python
Tool("Network Shares", network.action_list_shares, "List shared folders on this PC"),
```

Set `dangerous=True` (4th argument) if it changes anything on the machine.

## 3. Test it

Mock the command so the test runs on any OS (see `tests/test_actions.py`), then run `pytest`.

## 4. Document it

Add a line to `CHANGELOG.md` under *Unreleased*.
