# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Structured findings engine with severity-aware checks for disk space, RAM pressure, uptime, pending reboot, service health, device issues, firewall and Defender state.
- Findings panel in the Dashboard with background execution and summary added to generated text and HTML reports.
- Dangerous action confirmation prompts, action logging, per-tool disable/enable state, and cancel-aware long-running work.
- Dry-run preview for temp-file cleanup and a safer cancel-aware command runner.
- Support report metadata fields for client, ticket, technician and notes, along with JSON export support and redaction controls.
- Recent report history and print-friendly HTML styling for saved support reports.
- CLI support for listing recently saved reports without opening the GUI, including an optional `--limit` to show only the newest N files.

### Changed
- GUI action execution now updates state via the main thread queue instead of direct `after()` calls from worker threads.
- Support reports now include a Findings Summary at the top and can carry ticket context in both text and HTML output.

## [1.3.0] - 2026-10-01

### Added
- Proper package layout (`src/khanyo_toolkit/`) split into `actions/` (system, network, maintenance), `registry`, `reports`, `core`, `cli` and `app`.
- Headless mode: `khanyo --report txt|html [-o PATH]` builds a support report with no GUI, and `khanyo --list-tools` lists every tool.
- `python -m khanyo_toolkit` entry point and a `khanyo` console command.
- Automated tests (pytest) and GitHub Actions CI on Windows and Linux.
- `KHANYO_REPORTS_DIR` environment variable to change where reports are saved.
- Admin relaunch now also works for `python -m ...` and for packaged `.exe` builds.

### Fixed
- Health Snapshot printed a literal `\n` instead of line breaks.
- "Problem Devices" never showed its "no problem devices" message.
- "Battery Status" never showed its "no battery detected" message on desktops.
- Disk Space relied on `wmic`, which is removed from recent Windows 11 builds; it now uses PowerShell/CIM.
- Console output with non-UTF-8 characters could raise a decoding error; undecodable bytes are now replaced.
- "Relaunch as Administrator" reported success even if the user declined the UAC prompt.

### Changed
- Commands run without a shell wherever possible, and ping/DNS targets are validated, which removes a command-injection risk.
- Tools are defined as `Tool(...)` entries in one registry, so adding a tool is a one-line change.
- Minimum Python version is now 3.9.

## [1.2.0]
- Single-file release: technician diagnostics (hardware inventory, disk health, services, event errors, and more).
