# Building a standalone .exe

Technicians often want a single file they can drop on a USB stick.

```powershell
pip install -e ".[build]"
scripts\build_exe.bat
```

The result is `dist\KhanyoITToolkit.exe`.

Notes:

- The build uses `--windowed`, so no console window appears (this also means `--report` text output is not visible; use the normal `khanyo` command for headless runs).
- To make the exe always prompt for administrator rights, add `--uac-admin` to the PyInstaller command in `scripts/build_exe.bat`.
- Unsigned executables can trigger Windows SmartScreen or antivirus warnings. Code-signing the exe avoids this.
- Do not commit `dist/` or `build/`; attach the exe to a GitHub *Release* instead.
