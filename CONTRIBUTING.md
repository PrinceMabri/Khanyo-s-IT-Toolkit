# Contributing

Thanks for helping make Khanyo shine a bit brighter.

## Set up

```bash
git clone https://github.com/YOUR-USERNAME/khanyo-it-toolkit.git
cd khanyo-it-toolkit
python -m venv .venv
.venv\Scripts\activate          # Windows  (use: source .venv/bin/activate on Linux/macOS)
pip install -r requirements-dev.txt
```

## Before opening a pull request

```bash
ruff check .
pytest
```

Both must pass; CI runs the same checks on Windows and Linux.

## Guidelines

- **Read-only by default.** A tool that changes system state (restarts a service, deletes files, resets network settings) must be registered with `dangerous=True` so it is shown in red and kept out of automatic reports.
- **Never raise from an action.** Return a text report; use `run_command()` / `ps()` which already capture errors.
- **No shell strings with user input.** Pass commands as lists, and validate anything user-supplied (see `is_safe_host`).
- **Standard library only.** Keep the zero-dependency promise.
- Add a test for new behavior and an entry in `CHANGELOG.md`.

See [docs/ADDING_TOOLS.md](docs/ADDING_TOOLS.md) for a step-by-step guide to adding a tool.
