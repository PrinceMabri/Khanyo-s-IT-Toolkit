"""Tkinter GUI for the Khanyo IT Toolkit."""

import inspect
import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from .config import APP_TITLE, IS_WINDOWS, REPORTS_DIR
from .core import (
    get_cpu_usage,
    get_memory_usage,
    get_primary_drive_health,
    is_admin,
    open_path,
    relaunch_as_admin,
    write_action_log,
)
from .findings import Finding, Severity, run_all_checks
from .registry import CATEGORIES, REPORT_TOOLS, Tool
from .reports import collect_sections, default_report_name, render, write_report


class Tooltip:
    """Minimal hover tooltip for a widget."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.tip, text=self.text, background="#2c313c", foreground="#e6e9ef",
            relief="solid", borderwidth=1, padx=8, pady=4, font=("Segoe UI", 9),
        ).pack()

    def _hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class KhanyoApp(tk.Tk):
    GOLD = "#e8b64c"
    BG = "#151922"
    PANEL = "#1f2430"
    OUTPUT_BG = "#0e1117"
    TEXT_FG = "#e6e9ef"
    MUTED = "#8b93a3"
    LONG_RUNNING_TOOLS = {"Quick Health Scan", "Reset Network Adapter", "Traceroute"}

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x740")
        self.minsize(980, 620)
        self.configure(bg=self.BG)
        self.last_output = ""
        self._queue = queue.Queue()
        self._current_action = None
        self._cancel_event = None
        self._tool_buttons = {}
        self._build_style()
        self._build_header()
        self._build_body()
        self._queue_loop()
        self._log(f"{APP_TITLE} ready. \"Khanyo\" -- shining a light on your PC.\n")
        self._refresh_health()
        self._elevation_check()
        self._run_findings_checks()

    # ---- styling ----
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=self.BG)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("TNotebook", background=self.BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab", background=self.PANEL, foreground=self.TEXT_FG,
            padding=(16, 8), font=("Segoe UI", 10),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.GOLD)],
            foreground=[("selected", "#151922")],
        )
        style.configure(
            "Tool.TButton", background=self.PANEL, foreground=self.TEXT_FG,
            font=("Segoe UI", 10), padding=10, borderwidth=0,
        )
        style.map("Tool.TButton", background=[("active", "#2c3444")])
        style.configure(
            "Danger.TButton", background="#3a2130", foreground="#f1a7b8",
            font=("Segoe UI", 10), padding=10, borderwidth=0,
        )
        style.map("Danger.TButton", background=[("active", "#552634")])
        style.configure(
            "Gold.TButton", background=self.GOLD, foreground="#151922",
            font=("Segoe UI", 10, "bold"), padding=12, borderwidth=0,
        )
        style.map("Gold.TButton", background=[("active", "#f4c86a")])
        style.configure("Title.TLabel", background=self.BG, foreground=self.TEXT_FG,
                        font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", background=self.BG, foreground=self.GOLD,
                        font=("Segoe UI", 10, "bold"))
        style.configure("Status.TLabel", background=self.BG, foreground=self.MUTED,
                        font=("Segoe UI", 9))

    # ---- header ----
    def _build_header(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=18, pady=(16, 4))

        title_row = ttk.Frame(top)
        title_row.pack(fill="x")
        ttk.Label(title_row, text="\u2726 KHANYO IT TOOLKIT", style="Title.TLabel").pack(side="left")

        self.elevation_var = tk.StringVar(value="")
        self.elevation_label = ttk.Label(title_row, textvariable=self.elevation_var, style="Sub.TLabel")
        self.elevation_label.pack(side="right", padx=(0, 4))

        self.relaunch_btn = ttk.Button(
            title_row, text="Relaunch as Administrator", style="Gold.TButton",
            command=self._relaunch, width=24,
        )
        self.cancel_btn = ttk.Button(
            title_row, text="Cancel", style="Tool.TButton",
            command=self._cancel_current_action, width=10,
        )
        self.cancel_btn.pack(side="right", padx=(0, 8))
        self.cancel_btn.pack_forget()

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(top, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", pady=(4, 0))

        quick = ttk.Frame(top)
        quick.pack(fill="x", pady=(8, 2))
        self.quick_health_var = tk.StringVar(value="Health: checking...")
        ttk.Label(quick, textvariable=self.quick_health_var, style="Status.TLabel").pack(side="left")
        ttk.Button(
            quick, text="Refresh Health", style="Tool.TButton",
            command=self._refresh_health,
        ).pack(side="right")

        self.progress_bar = ttk.Progressbar(top, mode="indeterminate")
        self.progress_bar.pack(fill="x", pady=(4, 0))
        self.progress_bar.pack_forget()

    def _refresh_health(self):
        def worker():
            cpu = get_cpu_usage()
            ram = get_memory_usage()
            disk = get_primary_drive_health()

            def fmt(value, suffix="%"):
                return "N/A" if value is None else f"{value:.1f}{suffix}"

            status = (
                f"Health snapshot  |  CPU {fmt(cpu)}  |  RAM {fmt(ram)}  |  "
                f"C: free {fmt(disk)}"
            )
            self.after(0, lambda: self.quick_health_var.set(status))

        threading.Thread(target=worker, daemon=True).start()

    def _elevation_check(self):
        if not IS_WINDOWS:
            self.elevation_var.set("Non-Windows OS detected -- limited functionality")
            return
        if is_admin():
            self.elevation_var.set("Running as Administrator")
        else:
            self.elevation_var.set("Not elevated")
            self.relaunch_btn.pack(side="right", padx=(0, 12))
            self._log(
                "NOTE: Not running as Administrator. DNS cache, print spooler, network "
                "reset, restore point and health scan actions may fail or be incomplete. "
                "Use the 'Relaunch as Administrator' button above if needed.\n"
            )

    def _relaunch(self):
        if relaunch_as_admin():
            self.destroy()
            sys.exit(0)
        else:
            messagebox.showerror(
                APP_TITLE,
                "Could not relaunch elevated. Please right-click the script/shortcut "
                "and choose 'Run as administrator'.",
            )

    # ---- body: notebook + output ----
    def _build_body(self):
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=18, pady=(6, 16))

        left = ttk.Frame(body, width=320)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        self.notebook = ttk.Notebook(left)
        self.notebook.pack(fill="both", expand=True)

        for category, tools in CATEGORIES.items():
            tab = ttk.Frame(self.notebook, style="Panel.TFrame")
            self.notebook.add(tab, text=category)
            if category == "Dashboard":
                findings_frame = ttk.Frame(tab, style="Panel.TFrame")
                findings_frame.pack(fill="both", expand=True, padx=10, pady=(10, 6))
                ttk.Label(findings_frame, text="Findings", style="Sub.TLabel").pack(anchor="w")
                self.findings_output = tk.Text(
                    findings_frame, height=12, width=28, bg=self.OUTPUT_BG, fg=self.TEXT_FG,
                    insertbackground=self.TEXT_FG, relief="flat", padx=8, pady=8, wrap="word",
                )
                self.findings_output.pack(fill="both", expand=True, pady=(6, 8))
                self.findings_output.tag_configure("ok", foreground="#84e1a7")
                self.findings_output.tag_configure("warning", foreground="#f0c36d")
                self.findings_output.tag_configure("critical", foreground="#f39aa2")
                self.run_checks_btn = ttk.Button(
                    findings_frame, text="Run Checks", style="Gold.TButton",
                    command=self._run_findings_checks,
                )
                self.run_checks_btn.pack(fill="x")

            for tool in tools:
                style_name = "Danger.TButton" if tool.dangerous else "Tool.TButton"
                b = ttk.Button(
                    tab, text=tool.label, style=style_name,
                    command=lambda t=tool: self._run_action(t),
                )
                b.pack(padx=10, pady=4, fill="x")
                self._tool_buttons[tool.label] = b
                Tooltip(b, tool.tooltip)

        self._build_reports_tab()

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        self.output = tk.Text(
            right, bg=self.OUTPUT_BG, fg=self.TEXT_FG, insertbackground=self.TEXT_FG,
            font=("Consolas", 10), wrap="word", relief="flat", padx=12, pady=12,
        )
        self.output.pack(side="left", fill="both", expand=True)
        self.output.tag_configure("dim", foreground=self.MUTED)
        self.output.tag_configure("gold", foreground=self.GOLD)

        scrollbar = ttk.Scrollbar(right, command=self.output.yview)
        scrollbar.pack(side="right", fill="y")
        self.output.configure(yscrollcommand=scrollbar.set)

    def _queue_loop(self):
        try:
            while True:
                item = self._queue.get_nowait()
                kind = item[0]
                if kind == "action":
                    _, label, result = item
                    self._on_action_done(label, result)
                elif kind == "findings":
                    _, findings = item
                    self._render_findings(findings)
        except queue.Empty:
            pass
        self.after(100, self._queue_loop)

    def _render_findings(self, findings):
        if not hasattr(self, "findings_output"):
            return
        self.findings_output.delete("1.0", "end")
        if not findings:
            self.findings_output.insert("end", "No findings yet.\n")
            return
        for item in findings:
            if isinstance(item, Finding):
                severity_name = item.severity.name
                title = item.title
                detail = item.detail
            else:
                severity_name = str(item.get("severity", "WARNING")).upper()
                title = item.get("title", "Unknown check")
                detail = item.get("detail", "")
            color = severity_name.lower()
            line = f"[{severity_name}] {title}\n{detail}\n\n"
            self.findings_output.insert("end", line, color)

    def _run_findings_checks(self):
        def worker():
            try:
                findings = run_all_checks()
            except Exception as exc:  # pragma: no cover - defensive UI guard
                findings = [Finding(Severity.WARNING, "Checks failed", str(exc), "system")]
            self._queue.put(("findings", findings))

        threading.Thread(target=worker, daemon=True).start()

    def _cancel_current_action(self):
        if self._cancel_event is not None:
            self._cancel_event.set()
            self.status_var.set("Cancellation requested...")

    def _set_button_state(self, label, state):
        button = self._tool_buttons.get(label)
        if button is not None:
            button.configure(state="normal" if state else "disabled")

    def _build_reports_tab(self):
        reports_tab = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.notebook.add(reports_tab, text="Reports")

        form = ttk.Frame(reports_tab, style="Panel.TFrame")
        form.pack(fill="x", padx=10, pady=(10, 8))

        self.report_client_var = tk.StringVar()
        self.report_ticket_var = tk.StringVar()
        self.report_technician_var = tk.StringVar()
        self.report_notes_var = tk.StringVar()
        self.report_redact_var = tk.BooleanVar(value=False)

        for label, var in [
            ("Client", self.report_client_var),
            ("Ticket", self.report_ticket_var),
            ("Technician", self.report_technician_var),
            ("Notes", self.report_notes_var),
        ]:
            row = ttk.Frame(form)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"{label}:", width=12).pack(side="left")
            ttk.Entry(row, textvariable=var, width=28).pack(side="left", fill="x", expand=True)

        tk.Checkbutton(
            form,
            text="Redact identity data in report",
            variable=self.report_redact_var,
            fg=self.TEXT_FG,
            bg=self.PANEL,
            activebackground=self.PANEL,
            activeforeground=self.TEXT_FG,
            selectcolor=self.PANEL,
        ).pack(anchor="w", pady=(6, 4))

        ttk.Button(
            reports_tab, text="Generate Support Report (.txt)", style="Gold.TButton",
            command=lambda: self._generate_report("txt"),
        ).pack(padx=10, pady=(4, 4), fill="x")
        ttk.Button(
            reports_tab, text="Generate Support Report (.html)", style="Gold.TButton",
            command=lambda: self._generate_report("html"),
        ).pack(padx=10, pady=4, fill="x")
        ttk.Button(
            reports_tab, text="Generate Support Report (.json)", style="Gold.TButton",
            command=lambda: self._generate_report("json"),
        ).pack(padx=10, pady=4, fill="x")
        ttk.Button(
            reports_tab, text="View Report History", style="Tool.TButton",
            command=self._view_report_history,
        ).pack(padx=10, pady=(16, 4), fill="x")
        ttk.Button(
            reports_tab, text="Copy Last Output", style="Tool.TButton",
            command=self._copy_output,
        ).pack(padx=10, pady=4, fill="x")
        ttk.Button(
            reports_tab, text="Open Reports Folder", style="Tool.TButton",
            command=self._open_reports_folder,
        ).pack(padx=10, pady=4, fill="x")
        ttk.Button(
            reports_tab, text="Clear Output", style="Tool.TButton",
            command=self._clear_output,
        ).pack(padx=10, pady=(16, 4), fill="x")

    # ---- logging / output pane ----
    def _log(self, text, dim=False):
        self.output.insert("end", text + "\n", ("dim",) if dim else ())
        self.output.see("end")
        self.last_output = self.output.get("1.0", "end")

    def _clear_output(self):
        self.output.delete("1.0", "end")
        self.last_output = ""

    def _copy_output(self):
        text = self.output.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo(APP_TITLE, "There's nothing to copy yet -- run a tool first.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("Output copied to clipboard.")

    def _open_reports_folder(self):
        os.makedirs(REPORTS_DIR, exist_ok=True)
        if not open_path(REPORTS_DIR):
            messagebox.showerror(APP_TITLE, f"Could not open folder: {REPORTS_DIR}")

    def _view_report_history(self):
        os.makedirs(REPORTS_DIR, exist_ok=True)
        reports = []
        for name in os.listdir(REPORTS_DIR):
            path = os.path.join(REPORTS_DIR, name)
            if os.path.isfile(path) and name.lower().endswith((".txt", ".html", ".json")):
                reports.append((os.path.getmtime(path), path))
        if not reports:
            messagebox.showinfo(APP_TITLE, "No support reports have been saved yet.")
            return
        summary = "\n".join(
            os.path.basename(path)
            for _, path in sorted(reports, key=lambda item: (item[0], os.path.basename(item[1])), reverse=True)[:10]
        )
        messagebox.showinfo(APP_TITLE, f"Recent reports:\n\n{summary}")

    # ---- running single actions in background threads ----
    def _run_action(self, tool: Tool):
        label = tool.label
        action_fn = tool.func
        if self._current_action is not None and self._current_action == label:
            return
        if tool.dangerous:
            if not messagebox.askyesno(
                APP_TITLE,
                f"{tool.label}\n\n{tool.tooltip}\n\nProceed with this action?",
            ):
                return

        self._current_action = label
        self._cancel_event = threading.Event() if label in self.LONG_RUNNING_TOOLS else None
        self._set_button_state(label, False)
        self.status_var.set(f"Running: {label} ...")
        self._log(f"\n>>> {label}  [{datetime.now().strftime('%H:%M:%S')}]")
        if label in self.LONG_RUNNING_TOOLS:
            self.progress_bar.pack(fill="x", pady=(4, 0))
            self.progress_bar.start(12)
            self.cancel_btn.pack(side="right", padx=(0, 8))

        def worker():
            try:
                kwargs = {}
                if self._cancel_event is not None:
                    sig = inspect.signature(action_fn)
                    if "cancel_event" in sig.parameters:
                        kwargs["cancel_event"] = self._cancel_event
                result = action_fn(**kwargs) if kwargs else action_fn()
            except Exception as e:
                result = f"Unexpected error while running '{label}': {e}"
            if tool.dangerous:
                detail = result.replace("\n", " ")[:200]
                success = "error" not in result.lower() and "cancelled" not in result.lower()
                write_action_log(label, success, detail)
            self._queue.put(("action", label, result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_action_done(self, label, result):
        self._log(result)
        self._current_action = None
        self._cancel_event = None
        self._set_button_state(label, True)
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.cancel_btn.pack_forget()
        self.status_var.set(f"Done: {label}")

    # ---- support report generation ----
    def _generate_report(self, fmt):
        self.status_var.set("Generating full support report -- this may take a moment...")
        self._log(f"\n>>> Generating full support report ({fmt}) ...", dim=True)

        def worker():
            sections = collect_sections(REPORT_TOOLS)
            self.after(0, lambda: self._save_report(sections, fmt))

        threading.Thread(target=worker, daemon=True).start()

    def _save_report(self, sections, fmt):
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filetypes = {
            "txt": [("Text file", "*.txt")],
            "html": [("HTML file", "*.html")],
            "json": [("JSON file", "*.json")],
        }.get(fmt, [("All files", "*.*")])

        path = filedialog.asksaveasfilename(
            title="Save Support Report",
            initialdir=REPORTS_DIR,
            initialfile=default_report_name(fmt),
            defaultextension=f".{fmt}",
            filetypes=filetypes + [("All files", "*.*")],
        )
        if not path:
            self._log("Report generated but not saved (dialog cancelled).")
            self.status_var.set("Report generated (not saved to file).")
            return

        try:
            write_report(
                path,
                render(
                    sections,
                    fmt,
                    client=self.report_client_var.get(),
                    ticket=self.report_ticket_var.get(),
                    technician=self.report_technician_var.get(),
                    notes=self.report_notes_var.get(),
                    redact=self.report_redact_var.get(),
                ),
            )
            self._log(f"Support report saved to: {path}")
            self.status_var.set(f"Report saved: {os.path.basename(path)}")
            if messagebox.askyesno(APP_TITLE, f"Support report saved to:\n{path}\n\nOpen it now?"):
                if fmt == "html":
                    webbrowser.open(path)
                else:
                    open_path(path)
        except Exception as e:
            self._log(f"Failed to save report: {e}")
            self.status_var.set("Failed to save report.")


def run_gui() -> None:
    app = KhanyoApp()
    app.mainloop()
