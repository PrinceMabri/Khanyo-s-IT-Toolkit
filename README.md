# ✦ Khanyo IT Toolkit

[![CI](https://github.com/YOUR-USERNAME/khanyo-it-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR-USERNAME/khanyo-it-toolkit/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

A Windows PC troubleshooting toolkit with a clean, categorized GUI. *Khanyo* means **"light"**: this tool is built to shine a light on what is going on inside a machine, fast.

It uses only the Python standard library, so there is nothing to install besides Python itself.

<!-- Add a screenshot: save it as docs/images/screenshot.png, then uncomment the next line -->
<!-- ![Khanyo IT Toolkit screenshot](docs/images/screenshot.png) -->

## Features

| Tab | What it does |
| --- | --- |
| **Dashboard** | Live CPU, memory and C: drive health at a glance |
| **System** | System info, hardware inventory, disk health, battery, uptime, startup programs, processes, installed software, Windows Update status, key services, problem devices, recent system errors |
| **Network** | IP config, Wi-Fi status, adapters, gateway and DNS diagnostics, ping, DNS test, traceroute, port test, active connections, firewall status |
| **Maintenance** | Restart print spooler, clean temp files, empty Recycle Bin, create restore point, DISM + SFC scan, battery report |
| **Reports** | One-click support report as `.txt`, `.html` or `.json`, ticket metadata, redaction, report history, copy output, open reports folder |

Tools that change the system (shown in red) are never included in the automatic support report.

## Requirements

- Windows 10 / 11 (most tools are Windows-only; the app starts on other OSes with limited functionality)
- Python 3.9 or newer, with Tkinter (included in the standard Windows installer)

## Quick start

```powershell
git clone https://github.com/YOUR-USERNAME/khanyo-it-toolkit.git
cd khanyo-it-toolkit
pip install -e .
khanyo
```

Or run it without installing:

```powershell
python -m khanyo_toolkit        # from the src folder:  cd src
```

Some actions (Clear DNS Cache, Restart Print Spooler, Reset Network Adapter, Create Restore Point, Quick Health Scan) need Administrator rights. If you are not elevated, the app shows a **Relaunch as Administrator** button.

## Command line

```text
khanyo                                      launch the GUI
khanyo --list-tools                         list every tool
khanyo --report-history                     list the most recent saved reports
khanyo --report-history --limit 5           list the 5 newest saved reports
khanyo --open-last-report                  open the newest saved report
khanyo --report html                        generate a support report, no GUI
khanyo --report json --client "Acme" --ticket "T-42" --technician "Sam"
khanyo --report txt -o C:\Temp\pc-report.txt
khanyo --version
```

Reports are saved to `Documents\Khanyo Reports` by default. Set the `KHANYO_REPORTS_DIR` environment variable to change that.

## Project layout

```text
khanyo-it-toolkit/
├── src/khanyo_toolkit/
│   ├── actions/
│   │   ├── system.py        # OS, hardware, disks, services, events
│   │   ├── network.py       # connectivity diagnostics and network repair
│   │   └── maintenance.py   # state-changing clean-up tasks
│   ├── app.py               # Tkinter GUI
│   ├── cli.py               # command-line entry point
│   ├── config.py            # constants and settings
│   ├── core.py              # command runner, admin helpers, validation
│   ├── registry.py          # every tool, grouped by tab
│   └── reports.py           # .txt / .html report generation
├── tests/                   # pytest suite
├── docs/                    # developer guides
├── scripts/                 # build helpers (PyInstaller)
├── .github/                 # CI workflow, issue and PR templates
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

## Adding your own tool

Write one function that returns text, then add one line to `registry.py`. The full walkthrough is in [docs/ADDING_TOOLS.md](docs/ADDING_TOOLS.md).

## Development

```powershell
pip install -r requirements-dev.txt
ruff check .
pytest
```

To build a single-file `.exe`, see [docs/BUILD_EXE.md](docs/BUILD_EXE.md).

## Safety notes

- Read-only tools only inspect your system. The red buttons modify it: they delete temp files, flush DNS, reset the network stack and so on. Read the tooltip before clicking.
- Support reports contain machine details (hostname, installed software, network configuration). Review a report before sharing it publicly.

## License

[MIT](LICENSE)
