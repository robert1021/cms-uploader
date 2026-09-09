"""
CMS Uploader - Full GUI (tkinter/ttk)
Fixes hybrid TUI issues:
- Single Tk root (no withdraw() popups)
- Password masked, VPN/CMS status always visible
- No silent failures - tables, progress, messageboxes
- File dialogs owned by main window, layouts consistent
- Bulk Uploader options restored, dry-run preview
"""
import os
import threading
import queue
import logging
import shutil
import time
import openpyxl
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from config import APP_NAME, CMS_NETWORK_PATH, CMS_TARGET_DRIVE
from enums import CMSTools, CMSPathTypes, CMSFolders, SubmissionsFileExcelColumns, WorkloadManagementFormNames
from path_finder import PathFinder
from utils import (
    is_connected_to_vpn, is_connected_to_cms, is_xlsx_file,
    validate_bulk_uploader_excel_columns, validate_path_builder_excel_columns,
    validate_interactive_path_builder_excel_column, get_non_empty_column_values,
    map_network_drive, clean_filename, is_workload_management_form
)
from constants import DRIVE_LETTER, CMS_FOLDER


# ---------- theme helpers ----------
BG = "#f4f6f8"
SIDEBAR_BG = "#1e2a3a"
SIDEBAR_ACTIVE = "#2a3f5f"
CARD_BG = "#ffffff"
PRIMARY = "#2563eb"
PRIMARY_HOVER = "#1d4ed8"
SUCCESS = "#059669"
DANGER = "#dc2626"
MUTED = "#64748b"
BORDER = "#e2e8f0"

FONTS = {
    "title": ("Segoe UI", 16, "bold"),
    "subtitle": ("Segoe UI", 10),
    "body": ("Segoe UI", 9),
    "small": ("Segoe UI", 8),
    "mono": ("Consolas", 8),
}

def make_tooltip(widget, text):
    # tooltips disabled - was stacking; no-op to keep call sites unchanged
    return


class StatusBar(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Status.TFrame")
        self.vpn_var = tk.StringVar(value="VPN: checking…")
        self.cms_var = tk.StringVar(value="CMS: checking…")
        self.msg_var = tk.StringVar(value="Ready")
        self.vpn_label = ttk.Label(self, textvariable=self.vpn_var, style="Status.TLabel")
        self.cms_label = ttk.Label(self, textvariable=self.cms_var, style="Status.TLabel")
        self.msg_label = ttk.Label(self, textvariable=self.msg_var, style="StatusMuted.TLabel")
        self.vpn_label.pack(side="left", padx=12, pady=6)
        ttk.Separator(self, orient="vertical").pack(side="left", fill="y", padx=4, pady=4)
        self.cms_label.pack(side="left", padx=8)
        self.msg_label.pack(side="right", padx=12)
        self.refresh()

    def refresh(self):
        vpn = is_connected_to_vpn()
        cms = is_connected_to_cms()
        self.vpn_var.set(f"● VPN  {'Connected' if vpn else 'Not connected'}")
        self.cms_var.set(f"● CMS ({DRIVE_LETTER.strip(chr(92))}:)  {'Connected' if cms else 'Not connected'}")
        # color via foreground set directly
        self.vpn_label.configure(foreground=SUCCESS if vpn else DANGER)
        self.cms_label.configure(foreground=SUCCESS if cms else DANGER)
        # schedule next check every 8s
        self.after(8000, self.refresh)

    def set_message(self, msg, style="muted"):
        self.msg_var.set(msg)
        self.msg_label.configure(foreground=MUTED if style=="muted" else SUCCESS if style=="success" else DANGER)


class Sidebar(ttk.Frame):
    def __init__(self, parent, on_select):
        super().__init__(parent, style="Sidebar.TFrame", width=200)
        self.pack_propagate(False)
        self.on_select = on_select
        self.buttons = {}
        # logo
        hdr = tk.Frame(self, bg=SIDEBAR_BG)
        hdr.pack(fill="x", pady=(18, 10), padx=16)
        tk.Label(hdr, text=APP_NAME, bg=SIDEBAR_BG, fg="white", font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x")
        tk.Label(hdr, text="Health Canada  •  NHPD", bg=SIDEBAR_BG, fg="#94a3b8", font=FONTS["small"], anchor="w").pack(fill="x", pady=(2,0))
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=16, pady=10)
        # nav buttons
        nav_items = [
            ("Connect to CMS", CMSTools.CONNECT_TO_CMS.value, "Map Z: drive"),
            ("Path Builder", CMSTools.PATH_BUILDER.value, "Add Destination to Excel"),
            ("Interactive Builder", CMSTools.INTERACTIVE_PATH_BUILDER.value, "Create Excel from scratch"),
            ("Bulk Uploader", CMSTools.BULK_UPLOADER.value, "Copy files to CMS"),
        ]
        self._active = None
        for label, key, tip in nav_items:
            btn = tk.Button(self, text=f"  {label}", bg=SIDEBAR_BG, fg="#cbd5e1", activebackground=SIDEBAR_ACTIVE,
                            activeforeground="white", bd=0, anchor="w", font=("Segoe UI", 9), padx=8, pady=10,
                            relief="flat", cursor="hand2", command=lambda k=key: self.select(k))
            btn.pack(fill="x", padx=8, pady=2)
            make_tooltip(btn, tip)
            self.buttons[key] = btn
        # footer
        footer = tk.Frame(self, bg=SIDEBAR_BG)
        footer.pack(side="bottom", fill="x", padx=16, pady=12)
        tk.Label(footer, text="Tip: Press F5 to refresh\nVPN/CMS status", bg=SIDEBAR_BG, fg="#64748b", font=FONTS["small"], justify="left").pack(anchor="w")

    def select(self, key):
        if self._active:
            self.buttons[self._active].configure(bg=SIDEBAR_BG, fg="#cbd5e1")
        self._active = key
        self.buttons[key].configure(bg=SIDEBAR_ACTIVE, fg="white")
        self.on_select(key)


# ---------- reusable widgets ----------
def card(parent, title=None, subtitle=None):
    outer = tk.Frame(parent, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1, bd=0)
    inner = tk.Frame(outer, bg=CARD_BG)
    inner.pack(fill="both", expand=True, padx=18, pady=16)
    if title:
        tk.Label(inner, text=title, bg=CARD_BG, fg="#0f172a", font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
        if subtitle:
            tk.Label(inner, text=subtitle, bg=CARD_BG, fg=MUTED, font=FONTS["small"], anchor="w", wraplength=680, justify="left").pack(fill="x", pady=(2,8))
        else:
            tk.Frame(inner, height=8, bg=CARD_BG).pack()
    body = tk.Frame(inner, bg=CARD_BG)
    body.pack(fill="both", expand=True)
    return outer, body

def labeled_entry(parent, label, placeholder="", is_password=False, width=52):
    row = tk.Frame(parent, bg=CARD_BG)
    row.pack(fill="x", pady=4)
    tk.Label(row, text=label, bg=CARD_BG, fg="#334155", font=FONTS["body"], width=18, anchor="w").pack(side="left")
    var = tk.StringVar()
    ent = ttk.Entry(row, textvariable=var, width=width, show="•" if is_password else "")
    ent.pack(side="left", fill="x", expand=True, padx=(8,0))
    if placeholder:
        ent.configure(style="Placeholder.TEntry")
    return var, ent, row

def labeled_combo(parent, label, values, width=50):
    row = tk.Frame(parent, bg=CARD_BG)
    row.pack(fill="x", pady=4)
    tk.Label(row, text=label, bg=CARD_BG, fg="#334155", font=FONTS["body"], width=18, anchor="w").pack(side="left")
    var = tk.StringVar(value=values[0] if values else "")
    cb = ttk.Combobox(row, textvariable=var, values=values, state="readonly", width=width)
    cb.pack(side="left", fill="x", expand=True, padx=(8,0))
    return var, cb, row

def file_row(parent, label, var, browse_cmd, filetypes="Excel files (*.xlsx)"):
    row = tk.Frame(parent, bg=CARD_BG)
    row.pack(fill="x", pady=4)
    tk.Label(row, text=label, bg=CARD_BG, fg="#334155", font=FONTS["body"], width=18, anchor="w").pack(side="left")
    ent = ttk.Entry(row, textvariable=var, width=52)
    ent.pack(side="left", fill="x", expand=True, padx=(8,8))
    btn = ttk.Button(row, text="Browse…", style="Secondary.TButton", command=browse_cmd, width=10)
    btn.pack(side="left")
    return ent, btn, row

def primary_button(parent, text, command):
    btn = tk.Button(parent, text=text, bg=PRIMARY, fg="white", activebackground=PRIMARY_HOVER, activeforeground="white",
                    bd=0, font=("Segoe UI", 9, "bold"), padx=18, pady=8, cursor="hand2", command=command)
    # hover
    btn.bind("<Enter>", lambda e: btn.configure(bg=PRIMARY_HOVER))
    btn.bind("<Leave>", lambda e: btn.configure(bg=PRIMARY))
    return btn

def secondary_button(parent, text, command):
    return ttk.Button(parent, text=text, style="Secondary.TButton", command=command)


# ---------- Frames ----------
class ConnectFrame(ttk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent)
        self.status_bar = status_bar
        self.configure(style="Content.TFrame")
        outer, body = card(self, "Connect to CMS", "Maps the CMS SharePoint drive to Z:. Requires VPN. Your credentials are not stored.")
        outer.pack(fill="x", padx=16, pady=16)

        self.user_var, _, _ = labeled_entry(body, "Username", placeholder="e.g. hc\\jsmith")
        self.pass_var, self.pass_ent, _ = labeled_entry(body, "Password", is_password=True)
        # show/hide
        self.show_var = tk.BooleanVar(value=False)
        def toggle_show():
            self.pass_ent.configure(show="" if self.show_var.get() else "•")
        chk = ttk.Checkbutton(body, text="Show password", variable=self.show_var, command=toggle_show)
        chk.pack(anchor="w", padx=(150,0), pady=2)

        btn_row = tk.Frame(body, bg=CARD_BG)
        btn_row.pack(fill="x", pady=(12,0))
        self.connect_btn = primary_button(btn_row, "Connect to CMS", self.do_connect)
        self.connect_btn.pack(side="left")
        ttk.Button(btn_row, text="Test connection", style="Secondary.TButton", command=self.test).pack(side="left", padx=8)

        self.result = tk.Label(body, text="", bg=CARD_BG, fg=MUTED, font=FONTS["small"], anchor="w", justify="left", wraplength=600)
        self.result.pack(fill="x", pady=(10,0))

        # info card
        outer2, body2 = card(self, "Connection status")
        outer2.pack(fill="both", expand=True, padx=16, pady=(0,16))
        self.info = tk.Label(body2, text="", bg=CARD_BG, fg="#334155", font=FONTS["mono"], anchor="w", justify="left")
        self.info.pack(fill="x")
        self.refresh_info()
        # hint
        tk.Label(self, text="Stored on Z: →  " + CMS_NETWORK_PATH, bg=BG, fg=MUTED, font=FONTS["small"]).pack(pady=4)

    def refresh_info(self):
        vpn = is_connected_to_vpn()
        cms = is_connected_to_cms()
        lines = [
            f"VPN (Y:\\HC):  {'✓ Connected' if vpn else '✗ Not connected — connect VPN first'}",
            f"CMS (Z:):      {'✓ Connected — tools ready' if cms else '✗ Not connected — click Connect above'}",
            f"Target: {CMS_TARGET_DRIVE}  →  {CMS_NETWORK_PATH}",
        ]
        self.info.configure(text="\n".join(lines))
        self.after(3000, self.refresh_info)

    def test(self):
        vpn = is_connected_to_vpn()
        cms = is_connected_to_cms()
        if not vpn:
            messagebox.showwarning("VPN not connected", "Y:\\HC not found. Connect to VPN before testing CMS.", parent=self)
            return
        if cms:
            messagebox.showinfo("Connected", f"CMS is reachable at {os.path.join(DRIVE_LETTER, CMS_FOLDER)}", parent=self)
        else:
            messagebox.showwarning("Not connected", "CMS drive not found. Use Connect to CMS.", parent=self)

    def do_connect(self):
        user = self.user_var.get().strip()
        pwd = self.pass_var.get()
        if not user or not pwd:
            self.result.configure(text="Enter both username and password.", fg=DANGER)
            return
        self.connect_btn.configure(state="disabled", text="Connecting…")
        self.result.configure(text="Mapping network drive — this may take a few seconds…", fg=MUTED)
        self.status_bar.set_message("Connecting to CMS…")
        def worker():
            try:
                if is_connected_to_cms():
                    ok, msg = True, "Already connected to CMS"
                else:
                    ok = map_network_drive(CMS_TARGET_DRIVE, CMS_NETWORK_PATH, username=user, password=pwd)
                    msg = "Connected successfully." if ok else "Failed to connect — check username/password and VPN."
                self.after(0, lambda: self._done(ok, msg))
            except Exception as e:
                self.after(0, lambda: self._done(False, f"Error: {e}"))
        threading.Thread(target=worker, daemon=True).start()

    def _done(self, ok, msg):
        self.connect_btn.configure(state="normal", text="Connect to CMS")
        self.result.configure(text=msg, fg=SUCCESS if ok else DANGER)
        self.status_bar.set_message(msg, "success" if ok else "error")
        self.status_bar.refresh()
        if ok:
            messagebox.showinfo("CMS", msg, parent=self)


class PathBuilderFrame(ttk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent)
        self.status_bar = status_bar
        self.configure(style="Content.TFrame")
        outer, body = card(self, "Path Builder", "Adds a Destination column to an existing Excel file (Submission | Source → Destination).")
        outer.pack(fill="x", padx=16, pady=16)

        self.file_var = tk.StringVar()
        def browse():
            p = filedialog.askopenfilename(parent=self, title="Select submissions Excel file", filetypes=[("Excel files", "*.xlsx")])
            if p: self.file_var.set(p)
        file_row(body, "Excel file", self.file_var, browse)
        tk.Label(body, text="Columns must be: Submission | Source  (Destination will be added)", bg=CARD_BG, fg=MUTED, font=FONTS["small"]).pack(anchor="w", padx=(150,0))

        path_types = [CMSPathTypes.PRODUCT.value, CMSPathTypes.PRODUCT_POST_LICENCE_FOLDER.value,
                      CMSPathTypes.PRODUCT_CORRESPONDENCE_GENERAL_FOLDER.value, CMSPathTypes.PRODUCT_DECISION_FOLDER.value]
        self.ptype_var, _, _ = labeled_combo(body, "Path type", path_types)

        btn_row = tk.Frame(body, bg=CARD_BG)
        btn_row.pack(fill="x", pady=(14,0))
        self.run_btn = primary_button(btn_row, "Build paths  →  update Excel", self.run)
        self.run_btn.pack(side="left")
        ttk.Button(btn_row, text="Preview first 5 submissions", style="Secondary.TButton", command=self.preview).pack(side="left", padx=8)

        self.log = tk.Label(body, text="", bg=CARD_BG, fg=MUTED, font=FONTS["small"], anchor="w", justify="left", wraplength=620)
        self.log.pack(fill="x", pady=(10,0))

        # results table
        outer2, body2 = card(self, "Preview / Results")
        outer2.pack(fill="both", expand=True, padx=16, pady=(0,16))
        cols = ("Submission", "Destination", "Status")
        self.tree = ttk.Treeview(body2, columns=cols, show="headings", height=8)
        for c, w in zip(cols, (180, 420, 90)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        vs = ttk.Scrollbar(body2, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")

    def _validate_common(self):
        fp = self.file_var.get().strip()
        if not fp or not os.path.isfile(fp):
            messagebox.showerror("File", "Select a valid .xlsx file.", parent=self); return None
        if not is_xlsx_file(fp):
            messagebox.showerror("File", "File must be .xlsx", parent=self); return None
        if not is_connected_to_vpn():
            messagebox.showerror("VPN", "Not connected to VPN (Y:\\HC missing). Connect VPN first.", parent=self); return None
        if not is_connected_to_cms():
            messagebox.showerror("CMS", "CMS drive not connected. Go to Connect to CMS first.", parent=self); return None
        return fp

    def preview(self):
        fp = self._validate_common()
        if not fp: return
        try:
            wb = openpyxl.load_workbook(fp, read_only=True, data_only=True)
            ws = wb.active
            subs = get_non_empty_column_values(ws, "A")[0:5]
            wb.close()
            if not subs:
                messagebox.showinfo("Preview", "No submissions found in column A (below header).", parent=self); return
            finder = PathFinder()
            d = finder.find_cms_paths_for_submissions(subs, self.ptype_var.get())
            self.tree.delete(*self.tree.get_children())
            for s in subs:
                p = d.get(s, "")
                self.tree.insert("", "end", values=(s, p or "— not found", "✓" if p else "✗"))
            self.log.configure(text=f"Previewed {len(subs)} submissions.", fg=MUTED)
        except Exception as e:
            messagebox.showerror("Preview failed", str(e), parent=self)

    def run(self):
        fp = self._validate_common()
        if not fp: return
        ptype = self.ptype_var.get()
        self.run_btn.configure(state="disabled", text="Building…")
        self.log.configure(text="Resolving CMS paths — this reads the CMS drive and may take a minute for large files…", fg=MUTED)
        self.status_bar.set_message("Building paths…")
        self.tree.delete(*self.tree.get_children())
        def worker():
            try:
                # reuse handle logic but inline for better feedback
                wb = openpyxl.load_workbook(fp)
                ws = wb.active
                a = ws.cell(row=1, column=1).value
                b = ws.cell(row=1, column=2).value
                if not validate_path_builder_excel_columns(a, b):
                    raise ValueError(f"Expected headers 'Submission' | 'Source', found '{a}' | '{b}'")
                ws.cell(row=1, column=3).value = SubmissionsFileExcelColumns.DESTINATION.value
                submissions = get_non_empty_column_values(ws, "A")
                if not submissions:
                    raise ValueError("No submissions found in column A.")
                finder = PathFinder()
                # simple console shim for path_finder progress
                class Shim:
                    def print(self, *args, **kwargs): pass
                d = finder.find_cms_paths_for_submissions(submissions, ptype, console=Shim())
                for idx, row in enumerate(ws.iter_rows(min_row=2, max_col=2, values_only=True), start=2):
                    sub = row[0]
                    if sub:
                        ws.cell(row=idx, column=3).value = d.get(sub, "")
                wb.save(fp)
                self.after(0, lambda: self._done_ok(fp, submissions, d))
            except Exception as e:
                self.after(0, lambda: self._done_err(str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def _done_ok(self, fp, subs, d):
        self.run_btn.configure(state="normal", text="Build paths  →  update Excel")
        self.log.configure(text=f"Done — updated {fp} with {len(subs)} destinations.", fg=SUCCESS)
        self.status_bar.set_message("Paths built successfully", "success")
        self.tree.delete(*self.tree.get_children())
        for s in subs[:50]:
            p = d.get(s, "")
            self.tree.insert("", "end", values=(s, p or "— not found", "✓" if p else "✗"))
        if len(subs) > 50:
            self.tree.insert("", "end", values=(f"… and {len(subs)-50} more", "", ""))
        messagebox.showinfo("Path Builder", f"Success — Destination column written to:\n{fp}\n\nFound {sum(1 for v in d.values() if v)} / {len(subs)} paths.", parent=self)

    def _done_err(self, msg):
        self.run_btn.configure(state="normal", text="Build paths  →  update Excel")
        self.log.configure(text=msg, fg=DANGER)
        self.status_bar.set_message("Build failed", "error")
        messagebox.showerror("Path Builder failed", msg, parent=self)


class InteractiveBuilderFrame(ttk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent)
        self.status_bar = status_bar
        self.configure(style="Content.TFrame")
        outer, body = card(self, "Interactive Path Builder", "Create a new Excel from scratch. Enter submissions manually or from a file, pick source files, and generate Destinations.")
        outer.pack(fill="x", padx=16, pady=16)

        self.mode_var = tk.StringVar(value="file")
        mode_row = tk.Frame(body, bg=CARD_BG)
        mode_row.pack(fill="x", pady=2)
        tk.Label(mode_row, text="Submissions from", bg=CARD_BG, fg="#334155", font=FONTS["body"], width=18, anchor="w").pack(side="left")
        ttk.Radiobutton(mode_row, text="Excel file", variable=self.mode_var, value="file", command=self._toggle_mode).pack(side="left", padx=6)
        ttk.Radiobutton(mode_row, text="Manual entry", variable=self.mode_var, value="manual", command=self._toggle_mode).pack(side="left", padx=6)

        self.file_var = tk.StringVar()
        def browse_in():
            p = filedialog.askopenfilename(parent=self, title="Select submissions Excel", filetypes=[("Excel files", "*.xlsx")])
            if p: self.file_var.set(p)
        self.file_ent, _, self.file_row = file_row(body, "Submissions file", self.file_var, browse_in)

        self.manual_var = tk.StringVar()
        self.manual_lbl = tk.Label(body, text="Submission IDs (comma-separated)", bg=CARD_BG, fg="#334155", font=FONTS["body"])
        self.manual_ent = ttk.Entry(body, textvariable=self.manual_var, width=52)
        # not packed initially

        path_types = [CMSPathTypes.PRODUCT.value, CMSPathTypes.PRODUCT_POST_LICENCE_FOLDER.value,
                      CMSPathTypes.PRODUCT_CORRESPONDENCE_GENERAL_FOLDER.value, CMSPathTypes.PRODUCT_DECISION_FOLDER.value]
        self.ptype_var, _, _ = labeled_combo(body, "Path type", path_types)

        self.same_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text="Upload the same files to every submission", variable=self.same_var).pack(anchor="w", padx=(150,0), pady=6)

        self.files_label = tk.Label(body, text="No source files selected.", bg=CARD_BG, fg=MUTED, font=FONTS["small"], anchor="w")
        self.files_label.pack(fill="x", pady=2)
        btn_row = tk.Frame(body, bg=CARD_BG)
        btn_row.pack(fill="x", pady=4)
        ttk.Button(btn_row, text="Select source files…", style="Secondary.TButton", command=self.pick_files).pack(side="left")
        ttk.Button(btn_row, text="Clear", style="Secondary.TButton", command=self.clear_files).pack(side="left", padx=8)
        self.picked_files = []

        out_row = tk.Frame(body, bg=CARD_BG)
        out_row.pack(fill="x", pady=6)
        tk.Label(out_row, text="Save as", bg=CARD_BG, fg="#334155", font=FONTS["body"], width=18, anchor="w").pack(side="left")
        self.out_var = tk.StringVar(value=str(Path.cwd() / "output.xlsx"))
        ttk.Entry(out_row, textvariable=self.out_var, width=52).pack(side="left", fill="x", expand=True, padx=(8,8))
        ttk.Button(out_row, text="Browse…", style="Secondary.TButton", command=self.pick_out).pack(side="left")

        act = tk.Frame(body, bg=CARD_BG)
        act.pack(fill="x", pady=(12,0))
        self.run_btn = primary_button(act, "Generate Excel", self.run)
        self.run_btn.pack(side="left")
        self.log = tk.Label(body, text="", bg=CARD_BG, fg=MUTED, font=FONTS["small"], wraplength=620, justify="left")
        self.log.pack(fill="x", pady=(8,0))
        self._toggle_mode()

        # preview
        outer2, body2 = card(self, "Preview")
        outer2.pack(fill="both", expand=True, padx=16, pady=(0,16))
        cols = ("Submission", "Source", "Destination")
        self.tree = ttk.Treeview(body2, columns=cols, show="headings", height=7)
        for c, w in zip(cols, (150, 300, 240)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        vs = ttk.Scrollbar(body2, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")

    def _toggle_mode(self):
        is_file = self.mode_var.get() == "file"
        # show/hide file vs manual
        if is_file:
            self.file_row.pack(fill="x", pady=4)
            self.manual_lbl.pack_forget()
            self.manual_ent.pack_forget()
        else:
            self.file_row.pack_forget()
            self.manual_lbl.pack(fill="x", pady=(6,2))
            self.manual_ent.pack(fill="x", pady=2)

    def pick_files(self):
        files = filedialog.askopenfilenames(parent=self, title="Select source files")
        if files:
            self.picked_files = list(files)
            self.files_label.configure(text=f"{len(files)} file(s):  " + ", ".join(os.path.basename(f) for f in files[:3]) + (" …" if len(files)>3 else ""), fg="#334155")
            self._refresh_preview()

    def clear_files(self):
        self.picked_files = []
        self.files_label.configure(text="No source files selected.", fg=MUTED)
        self.tree.delete(*self.tree.get_children())

    def pick_out(self):
        p = filedialog.asksaveasfilename(parent=self, title="Save Excel as", defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")], initialfile="output.xlsx")
        if p: self.out_var.set(p)

    def _refresh_preview(self):
        # lightweight preview without CMS lookup
        subs = []
        if self.mode_var.get() == "manual":
            subs = [s.strip() for s in self.manual_var.get().split(",") if s.strip()]
        else:
            fp = self.file_var.get().strip()
            if fp and os.path.isfile(fp):
                try:
                    wb = openpyxl.load_workbook(fp, read_only=True, data_only=True)
                    ws = wb.active
                    subs = get_non_empty_column_values(ws, "A")
                    wb.close()
                except: subs = []
        self.tree.delete(*self.tree.get_children())
        if not subs or not self.picked_files:
            return
        same = self.same_var.get()
        # show first few rows as they will be written
        count = 0
        for sub in subs[:5]:
            for f in (self.picked_files if same else self.picked_files[:1]):
                self.tree.insert("", "end", values=(sub, f, "… will resolve"))
                count += 1
                if count >= 10: break
            if count >= 10: break

    def run(self):
        ptype = self.ptype_var.get()
        out = self.out_var.get().strip()
        if not out.lower().endswith(".xlsx"):
            out += ".xlsx"
        # validate
        if not is_connected_to_vpn():
            messagebox.showerror("VPN", "Not connected to VPN.", parent=self); return
        if not is_connected_to_cms():
            messagebox.showerror("CMS", "CMS not connected. Go to Connect first.", parent=self); return
        # get submissions
        submissions = []
        wb_in = None
        if self.mode_var.get() == "file":
            fp = self.file_var.get().strip()
            if not fp or not os.path.isfile(fp):
                messagebox.showerror("File", "Select a valid submissions Excel file.", parent=self); return
            if not is_xlsx_file(fp):
                messagebox.showerror("File", "Must be .xlsx", parent=self); return
            try:
                wb_in = openpyxl.load_workbook(fp)
                ws = wb_in.active
                if not validate_interactive_path_builder_excel_column(ws.cell(row=1, column=1).value or ""):
                    messagebox.showerror("Excel", f"Expected header 'Submission' in A1, found '{ws.cell(row=1, column=1).value}'", parent=self); return
                submissions = get_non_empty_column_values(ws, "A")
            except Exception as e:
                messagebox.showerror("Excel", str(e), parent=self); return
        else:
            raw = self.manual_var.get().strip()
            submissions = [s.strip() for s in raw.split(",") if s.strip()]
            if not submissions:
                messagebox.showerror("Submissions", "Enter at least one submission ID.", parent=self); return
        if not submissions:
            messagebox.showerror("Submissions", "No submissions found.", parent=self); return
        # files handling
        if not self.picked_files and not self.same_var.get():
            # per-submission picking: prompt now sequentially
            # need to collect per-submission files
            pass # handled below

        self.run_btn.configure(state="disabled", text="Resolving CMS paths…")
        self.log.configure(text=f"Resolving {len(submissions)} submissions — querying CMS…", fg=MUTED)
        self.status_bar.set_message("Interactive build — resolving…")

        def worker():
            try:
                finder = PathFinder()
                class Shim:
                    def print(self, *a, **k): pass
                path_map = finder.find_cms_paths_for_submissions(submissions, ptype, console=Shim())

                # Determine source files per submission
                per_sub_files = {}
                if self.same_var.get():
                    if not self.picked_files:
                        raise ValueError("Select source files first (same files for all).")
                    for s in submissions:
                        per_sub_files[s] = list(self.picked_files)
                else:
                    # Need per-submission files - if we already have picked files we treat as fallback,
                    # otherwise we must ask via dialog on main thread
                    # For GUI, we require files selected; per-submission dialog would block worker
                    # So enforce: in 'different files' mode, user must have organized files externally and use Path Builder
                    # To support interactive per-submission, we ask on main thread before starting worker.
                    # Here we already have picked_files as template for all; ask to confirm
                    raise ValueError("For 'different files per submission', use Path Builder workflow or select files and we will duplicate per submission. "
                                     "Tip: check 'same files' or run once per submission.")

                # Build output workbook
                if wb_in is not None:
                    wb = wb_in
                    ws = wb.active
                    ws.cell(row=1, column=2).value = SubmissionsFileExcelColumns.SOURCE.value
                    ws.cell(row=1, column=3).value = SubmissionsFileExcelColumns.DESTINATION.value
                    # clear old data below header (keep col A)
                    for row in ws.iter_rows(min_row=2, max_col=3):
                        for c in row[1:]:
                            c.value = None
                    r = 2
                else:
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.cell(row=1, column=1).value = SubmissionsFileExcelColumns.SUBMISSION.value
                    ws.cell(row=1, column=2).value = SubmissionsFileExcelColumns.SOURCE.value
                    ws.cell(row=1, column=3).value = SubmissionsFileExcelColumns.DESTINATION.value
                    r = 2

                # Write rows
                for sub in submissions:
                    dest = path_map.get(sub, "")
                    for f in per_sub_files.get(sub, []):
                        ws.cell(row=r, column=1).value = sub
                        ws.cell(row=r, column=2).value = f
                        ws.cell(row=r, column=3).value = dest
                        r += 1

                wb.save(out)
                self.after(0, lambda: self._done_ok(out, submissions, path_map, per_sub_files))
            except Exception as e:
                self.after(0, lambda: self._done_err(str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def _done_ok(self, out, subs, pmap, per_files):
        self.run_btn.configure(state="normal", text="Generate Excel")
        total_files = sum(len(v) for v in per_files.values())
        self.log.configure(text=f"Saved {out} — {len(subs)} submissions, {total_files} rows.", fg=SUCCESS)
        self.status_bar.set_message("Excel generated", "success")
        self.tree.delete(*self.tree.get_children())
        for s in subs[:20]:
            for f in per_files.get(s, [])[:2]:
                self.tree.insert("", "end", values=(s, os.path.basename(f), pmap.get(s, "") or "-"))
        messagebox.showinfo("Done", f"Generated:\n{out}\n\n{len(subs)} submissions × {len(self.picked_files)} file(s)", parent=self)

    def _done_err(self, msg):
        self.run_btn.configure(state="normal", text="Generate Excel")
        self.log.configure(text=msg, fg=DANGER)
        self.status_bar.set_message("Build failed", "error")
        messagebox.showerror("Interactive Builder failed", msg, parent=self)


class BulkUploaderFrame(ttk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent)
        self.status_bar = status_bar
        self.configure(style="Content.TFrame")
        outer, body = card(self, "Bulk Uploader", "Copies Source → Destination per Excel row. Validates headers, creates missing CMS folders, logs progress.")
        outer.pack(fill="x", padx=16, pady=16)

        self.file_var = tk.StringVar()
        def browse():
            p = filedialog.askopenfilename(parent=self, title="Select Bulk Uploader Excel", filetypes=[("Excel files", "*.xlsx")])
            if p: self.file_var.set(p)
        file_row(body, "Excel file", self.file_var, browse)
        tk.Label(body, text="Columns: Submission | Source | Destination  (Destination from Path Builder)", bg=CARD_BG, fg=MUTED, font=FONTS["small"]).pack(anchor="w", padx=(150,0))

        opts = tk.Frame(body, bg=CARD_BG)
        opts.pack(fill="x", pady=8)
        self.gen_log_var = tk.BooleanVar(value=True)
        self.create_missing_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Generate log file (bulkUploader.log next to Excel)", variable=self.gen_log_var).pack(side="left", padx=(150,0))
        ttk.Checkbutton(opts, text="Create missing CMS folders", variable=self.create_missing_var).pack(side="left", padx=16)

        btn_row = tk.Frame(body, bg=CARD_BG)
        btn_row.pack(fill="x", pady=6)
        self.dry_btn = ttk.Button(btn_row, text="Dry run — validate only", style="Secondary.TButton", command=self.dry_run)
        self.dry_btn.pack(side="left")
        self.run_btn = primary_button(btn_row, "Upload to CMS", self.run)
        self.run_btn.pack(side="left", padx=8)

        # progress
        prog_row = tk.Frame(body, bg=CARD_BG)
        prog_row.pack(fill="x", pady=(8,0))
        self.prog = ttk.Progressbar(prog_row, mode="determinate")
        self.prog.pack(fill="x", expand=True, side="left")
        self.prog_label = tk.Label(prog_row, text="0 / 0  0%", bg=CARD_BG, fg=MUTED, font=FONTS["small"], width=16, anchor="e")
        self.prog_label.pack(side="left", padx=8)

        # live current-file + stats row
        cur_row = tk.Frame(body, bg=CARD_BG)
        cur_row.pack(fill="x", pady=(6,0))
        self.current_var = tk.StringVar(value="")
        self.current_label = tk.Label(cur_row, textvariable=self.current_var, bg=CARD_BG, fg="#1e293b", font=FONTS["mono"], anchor="w", wraplength=620, justify="left")
        self.current_label.pack(side="left", fill="x", expand=True)
        self.elapsed_var = tk.StringVar(value="")
        tk.Label(cur_row, textvariable=self.elapsed_var, bg=CARD_BG, fg=MUTED, font=FONTS["mono"], width=10, anchor="e").pack(side="right", padx=(8,0))

        stats_row = tk.Frame(body, bg=CARD_BG)
        stats_row.pack(fill="x", pady=2)
        self.stats_var = tk.StringVar(value="")
        tk.Label(stats_row, textvariable=self.stats_var, bg=CARD_BG, fg=MUTED, font=FONTS["small"], anchor="w", justify="left").pack(side="left", fill="x", expand=True)

        self.log = tk.Label(body, text="", bg=CARD_BG, fg=MUTED, font=FONTS["small"], wraplength=620, justify="left")
        self.log.pack(fill="x", pady=4)

        outer2, body2 = card(self, "Live log  —  updates as each file is copied")
        outer2.pack(fill="both", expand=True, padx=16, pady=(0,16))
        self.text = tk.Text(body2, height=12, bg="#f8fafc", fg="#1e293b", font=FONTS["mono"], wrap="word", bd=0, highlightthickness=1, highlightbackground=BORDER)
        vs = ttk.Scrollbar(body2, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=vs.set)
        self.text.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        # colored tags for instant scan
        self.text.tag_configure("info", foreground="#334155")
        self.text.tag_configure("working", foreground=PRIMARY)
        self.text.tag_configure("success", foreground=SUCCESS)
        self.text.tag_configure("skip", foreground="#d97706")
        self.text.tag_configure("error", foreground=DANGER)
        self.text.tag_configure("muted", foreground=MUTED)
        self.text.configure(state="disabled")

    def _validate_common(self):
        fp = self.file_var.get().strip()
        if not fp or not os.path.isfile(fp):
            messagebox.showerror("File", "Select a valid .xlsx file.", parent=self); return None
        if not is_xlsx_file(fp):
            messagebox.showerror("File", "Must be .xlsx", parent=self); return None
        if not is_connected_to_vpn():
            messagebox.showerror("VPN", "Not connected to VPN.", parent=self); return None
        if not is_connected_to_cms():
            messagebox.showerror("CMS", "CMS not connected. Connect first.", parent=self); return None
        return fp

    def _append(self, msg, tag="info"):
        self.text.configure(state="normal")
        self.text.insert("end", msg + "\n", tag)
        self.text.see("end")
        self.text.configure(state="disabled")

    def dry_run(self):
        fp = self._validate_common()
        if not fp: return
        try:
            wb = openpyxl.load_workbook(fp, read_only=True, data_only=True)
            ws = wb.active
            a, b, c = ws.cell(row=1, column=1).value, ws.cell(row=1, column=2).value, ws.cell(row=1, column=3).value
            if not validate_bulk_uploader_excel_columns(a or "", b or "", c or ""):
                messagebox.showerror("Excel", f"Expected headers 'Submission' | 'Source' | 'Destination'\nFound '{a}' | '{b}' | '{c}'", parent=self); return
            rows = list(ws.iter_rows(min_row=2, max_col=3, values_only=True))
            wb.close()
            issues = []
            for i, r in enumerate(rows, start=2):
                if not r[0] and not r[1] and not r[2]:
                    continue
                if not r[1] or not os.path.isfile(str(r[1] or "")):
                    issues.append(f"Row {i}: Source not found → {r[1]}")
                if not r[2] or not str(r[2]).strip():
                    issues.append(f"Row {i}: Destination empty")
            msg = f"Dry run: {len(rows)} rows. {len(issues)} issue(s).\n" + ("\n".join(issues[:12]) + ("\n…" if len(issues)>12 else "") if issues else "✓ Headers and paths look good — ready to upload.")
            self._append(msg)
            self.log.configure(text=msg.splitlines()[0], fg=SUCCESS if not issues else DANGER)
            if not issues:
                messagebox.showinfo("Dry run", "Validation passed — ready to upload.", parent=self)
        except Exception as e:
            messagebox.showerror("Dry run failed", str(e), parent=self)

    def run(self):
        fp = self._validate_common()
        if not fp: return
        # validate headers first
        try:
            wb = openpyxl.load_workbook(fp, read_only=True, data_only=True)
            ws = wb.active
            a, b, c = ws.cell(row=1, column=1).value, ws.cell(row=1, column=2).value, ws.cell(row=1, column=3).value
            wb.close()
            if not validate_bulk_uploader_excel_columns(a or "", b or "", c or ""):
                messagebox.showerror("Excel", f"Expected 'Submission|Source|Destination', found '{a}|{b}|{c}'", parent=self); return
        except Exception as e:
            messagebox.showerror("Excel", str(e), parent=self); return

        if not messagebox.askyesno("Confirm upload", f"Upload files listed in:\n{fp}\n\nThis will copy files to CMS (Z:). Continue?", parent=self):
            return

        gen_log = self.gen_log_var.get()
        create_missing = self.create_missing_var.get()

        # --- reset UI for live feedback ---
        self.text.configure(state="normal"); self.text.delete("1.0", "end"); self.text.configure(state="disabled")
        self.prog.configure(value=0)
        self.prog_label.configure(text="0 / 0  0%")
        self.current_var.set("Starting… reading Excel…")
        self.elapsed_var.set("00:00")
        self.stats_var.set("Preparing…")
        self.run_btn.configure(state="disabled", text="Uploading… 0/0")
        self.dry_btn.configure(state="disabled")
        self.status_bar.set_message("Uploading to CMS… 0/0")
        self.log.configure(text="Starting…", fg=MUTED)

        q: queue.Queue = queue.Queue()
        start_ts = time.time()
        self._bulk_running = True

        def _fmt_elapsed(s: float) -> str:
            m, sec = divmod(int(s), 60)
            h, m = divmod(m, 60)
            return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"

        # helper to push colored log lines into the queue
        def qlog(msg: str, tag: str = "info"):
            q.put(("log", (msg, tag)))

        # --- pump runs on the main thread (started BEFORE worker) ---
        def pump():
            # live elapsed tick
            if getattr(self, "_bulk_running", False):
                self.elapsed_var.set(_fmt_elapsed(time.time() - start_ts))
            try:
                while True:
                    kind, payload = q.get_nowait()
                    if kind == "log":
                        if isinstance(payload, tuple) and len(payload) == 2:
                            msg, tag = payload
                        else:
                            msg, tag = payload, "info"
                        self._append(msg, tag)
                    elif kind == "current":
                        self.current_var.set(payload)
                        # also mirror short text in the small label + status bar
                        self.log.configure(text=payload[:120], fg=MUTED)
                        self.status_bar.set_message(payload[:90])
                    elif kind == "progress":
                        d, t = payload
                        pct = int(d * 100 / t) if t else 0
                        self.prog.configure(value=pct)
                        self.prog_label.configure(text=f"{d} / {t}  {pct}%")
                        self.run_btn.configure(text=f"Uploading… {d}/{t}")
                        self.status_bar.set_message(f"Uploading {d}/{t} ({pct}%)…")
                    elif kind == "stats":
                        # payload is dict {copied, skipped, errors, done, total}
                        self.stats_var.set(
                            f"Copied: {payload.get('copied', 0)}  ·  Skipped: {payload.get('skipped', 0)}  ·  Errors: {payload.get('errors', 0)}  ·  Done: {payload.get('done', 0)}/{payload.get('total', 0)}"
                        )
                    elif kind == "done":
                        d, t, stats = payload
                        self.prog.configure(value=100)
                        self.prog_label.configure(text=f"{d} / {t}  100%")
                        self.current_var.set(f"Done — {d}/{t} files")
                        self.stats_var.set(f"Copied: {stats.get('copied',0)}  ·  Skipped: {stats.get('skipped',0)}  ·  Errors: {stats.get('errors',0)}  ·  Done: {d}/{t}")
                        self.elapsed_var.set(_fmt_elapsed(time.time() - start_ts))
                        self._bulk_running = False
                        self._append(f"\nDone — processed {d}/{t} rows  ·  copied {stats.get('copied',0)} · skipped {stats.get('skipped',0)} · errors {stats.get('errors',0)} in {_fmt_elapsed(time.time()-start_ts)}", "muted")
                        self.log.configure(text=f"Done — {d} rows processed. Copied {stats.get('copied',0)}, skipped {stats.get('skipped',0)}.", fg=SUCCESS)
                        self.status_bar.set_message(f"Upload complete — {d}/{t} files in {_fmt_elapsed(time.time()-start_ts)}", "success")
                        self.run_btn.configure(state="normal", text="Upload to CMS")
                        self.dry_btn.configure(state="normal")
                        messagebox.showinfo("Bulk Uploader", f"Done — processed {d} rows.\nCopied: {stats.get('copied',0)}  Skipped: {stats.get('skipped',0)}  Errors: {stats.get('errors',0)}\nTime: {_fmt_elapsed(time.time()-start_ts)}\nLog (if enabled) next to Excel.", parent=self)
                    elif kind == "error":
                        self._append(f"Fatal: {payload}", "error")
                        self.log.configure(text=str(payload)[:120], fg=DANGER)
                        self.status_bar.set_message("Upload failed", "error")
                        self._bulk_running = False
                        self.run_btn.configure(state="normal", text="Upload to CMS")
                        self.dry_btn.configure(state="normal")
                        messagebox.showerror("Upload failed", payload, parent=self)
            except queue.Empty:
                pass
            if getattr(self, "_bulk_running", False):
                self.after(80, pump)
            else:
                # one final drain of any straggling logs
                try:
                    while True:
                        k, p = q.get_nowait()
                        if k == "log":
                            if isinstance(p, tuple) and len(p) == 2:
                                self._append(p[0], p[1])
                            else:
                                self._append(p)
                        elif k == "current":
                            self.current_var.set(p)
                except queue.Empty:
                    pass

        self.after(80, pump)

        def worker():
            import builtins
            orig_print = builtins.print

            def gui_append(s, tag="info"):
                qlog(s, tag)

            def patched_print(*args, **kwargs):
                # keep console output but also surface in live log
                txt = " ".join(str(a) for a in args)
                gui_append(txt, "muted")
                orig_print(*args, **kwargs)

            builtins.print = patched_print
            # live counters
            stats = {"copied": 0, "skipped": 0, "errors": 0, "done": 0, "total": 0}
            try:
                wb = openpyxl.load_workbook(fp)
                ws = wb.active
                rows = list(ws.iter_rows(min_row=2, max_col=3, values_only=True))
                total = len([r for r in rows if any(r)])
                stats["total"] = total
                q.put(("stats", dict(stats)))
                q.put(("progress", (0, total)))
                qlog(f"Found {total} row(s) to process", "info")
                self.after(0, lambda: self.current_var.set(f"Found {total} files — starting…"))
                if gen_log:
                    log_path = os.path.join(os.path.dirname(fp), "bulkUploader.log")
                    logging.basicConfig(level=logging.INFO, filename=log_path, filemode="w", format="%(asctime)s - %(levelname)s - %(message)s", force=True)
                    logging.info(f"File upload started - Excel: '{fp}' | Rows: {total} | create_missing={create_missing} | Log: '{log_path}'")
                    qlog(f"Logging to {log_path}", "muted")
                    q.put(("current", f"Logging to {log_path}"))
                done = 0
                for row in rows:
                    if not any(row):
                        continue
                    sub, src, dest = row[0], row[1], row[2]
                    submission = str(sub).strip() if sub is not None else ""
                    raw_src = str(src).strip() if src is not None else ""
                    raw_dest = str(dest).strip() if dest is not None else ""
                    cleaned_name = clean_filename(os.path.basename(raw_src)) if raw_src else ""
                    full_dest_path = os.path.join(raw_dest, cleaned_name) if raw_dest and cleaned_name else (raw_dest or cleaned_name or "")
                    # --- tell the UI what we're about to do (immediate feedback) ---
                    cur_msg = f"[{done+1}/{total}] {submission} - {os.path.basename(raw_src) or '(no file)'} -> {raw_dest or '(no destination)'}"
                    q.put(("current", cur_msg))
                    qlog(f"[{done+1}/{total}] {submission} - {raw_src} -> {raw_dest}", "working")
                    if gen_log:
                        logging.info(f"[{submission}] Working on file '{raw_src}' -> destination folder '{raw_dest}' | New full path: '{full_dest_path}'")
                    try:
                        src = raw_src
                        dest = raw_dest
                        outcome = None
                        if not dest.strip():
                            qlog(f"  -> Row destination empty, skipping", "skip")
                            if gen_log: logging.info(f"[{submission}] SKIP - Row destination empty for file '{raw_src}' | Submission: '{submission}' | No file created (destination was empty)")
                            stats["skipped"] += 1; outcome = "skip"
                            done += 1; stats["done"] = done
                            q.put(("progress", (done, total))); q.put(("stats", dict(stats)))
                            continue
                        if not os.path.exists(dest):
                            qlog(f"  -> Destination missing: {raw_dest}", "skip")
                            if gen_log: logging.info(f"[{submission}] Destination folder does not exist in CMS: '{raw_dest}' | File: '{raw_src}' | New full path would be: '{full_dest_path}'")
                            if create_missing:
                                os.makedirs(dest, exist_ok=True)
                                full_dest = os.path.join(dest, clean_filename(os.path.basename(src)))
                                shutil.copy2(src, full_dest)
                                qlog(f"  -> Created folder and copied -> {full_dest}", "success")
                                if gen_log: logging.info(f"[{submission}] COPIED (created missing folder) - file '{raw_src}' -> '{full_dest}' | Submission: '{submission}'")
                                stats["copied"] += 1; outcome = "copied"
                                target_folders = [CMSFolders.CORRESPONDENCE_GENERAL.value, CMSFolders.POST_LICENCE.value, CMSFolders.DECISION.value]
                                if any(dest.endswith(f) for f in target_folders):
                                    parent = os.path.dirname(dest)
                                    try:
                                        existing = os.listdir(parent)
                                    except: existing = []
                                    for item in CMSFolders.get_values():
                                        if item not in existing:
                                            try: os.makedirs(os.path.join(parent, item), exist_ok=True)
                                            except: pass
                                    qlog(f"  -> Ensured sibling CMS folders under {os.path.dirname(dest)}", "info")
                                    if gen_log: logging.info(f"[{submission}] Created sibling CMS folders under '{os.path.dirname(dest)}' for file '{raw_src}' | Submission: '{submission}'")
                            else:
                                qlog(f"  -> Skipping (create missing disabled)", "skip")
                                if gen_log: logging.info(f"[{submission}] SKIP (create_missing disabled) - file '{raw_src}' not copied - destination '{raw_dest}' missing | Would have been: '{full_dest_path}' | Submission: '{submission}'")
                                stats["skipped"] += 1; outcome = "skip"
                        elif not os.path.exists(os.path.join(dest, clean_filename(os.path.basename(src)))):
                            full_dest = os.path.join(dest, clean_filename(os.path.basename(src)))
                            shutil.copy2(src, full_dest)
                            qlog(f"  -> Copied -> {full_dest}", "success")
                            if gen_log: logging.info(f"[{submission}] COPIED - file '{raw_src}' -> '{full_dest}' | Submission: '{submission}'")
                            stats["copied"] += 1; outcome = "copied"
                        elif is_workload_management_form(os.path.join(dest, clean_filename(os.path.basename(src)))):
                            existing_full = os.path.join(dest, clean_filename(os.path.basename(src)))
                            qlog(f"  -> Workload form exists at {existing_full} - incrementing", "info")
                            if gen_log: logging.info(f"[{submission}] Workload Management Form exists at '{existing_full}' for file '{raw_src}' - incrementing filename | Submission: '{submission}'")
                            name_part, ext = os.path.splitext(clean_filename(os.path.basename(src)))
                            count = 0
                            fname = clean_filename(os.path.basename(src))
                            new_dest = os.path.join(dest, fname)
                            while os.path.exists(new_dest):
                                count += 1
                                fname = f"{name_part} ({count}){ext}"
                                new_dest = os.path.join(dest, fname)
                            shutil.copy2(src, new_dest)
                            qlog(f"  -> Workload form - incremented -> {new_dest}", "success")
                            if gen_log: logging.info(f"[{submission}] COPIED (workload form incremented) - file '{raw_src}' -> '{new_dest}' | Submission: '{submission}' | Original full path was '{existing_full}'")
                            stats["copied"] += 1; outcome = "copied"
                        else:
                            qlog(f"  -> Already exists, skipping: {full_dest_path}", "skip")
                            if gen_log: logging.info(f"[{submission}] SKIP - Already exists - file '{raw_src}' already at '{full_dest_path}' | Submission: '{submission}'")
                            stats["skipped"] += 1; outcome = "skip"
                    except Exception as e:
                        qlog(f"  !! Error: {e}", "error")
                        if gen_log: logging.error(f"[{submission}] ERROR - file '{raw_src}' -> '{full_dest_path}' | Submission: '{submission}' | Error: {e}")
                        stats["errors"] += 1; outcome = "error"
                    done += 1; stats["done"] = done
                    q.put(("progress", (done, total)))
                    q.put(("stats", dict(stats)))
                    # update current line with outcome
                    if outcome:
                        q.put(("current", f"[{done}/{total}] {submission} - {os.path.basename(raw_src) or ''}  [{outcome.upper()}]  -> {full_dest_path}"))
                q.put(("done", (done, total, dict(stats))))
            except Exception as e:
                q.put(("error", str(e)))
                qlog(f"Fatal error: {e}", "error")
            finally:
                builtins.print = orig_print

        threading.Thread(target=worker, daemon=True).start()


class CMSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — Health Canada")
        self.geometry("1050x720")
        self.minsize(980, 640)
        self.configure(bg=BG)
        # styles
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except: pass
        style.configure("Sidebar.TFrame", background=SIDEBAR_BG)
        style.configure("Content.TFrame", background=BG)
        style.configure("Status.TFrame", background="#ffffff")
        style.configure("Status.TLabel", background="#ffffff", foreground="#334155", font=FONTS["small"])
        style.configure("StatusMuted.TLabel", background="#ffffff", foreground=MUTED, font=FONTS["small"])
        style.configure("Secondary.TButton", font=FONTS["body"])
        style.configure("Treeview", rowheight=22, font=FONTS["small"])
        style.configure("Treeview.Heading", font=("Segoe UI", 8, "bold"))
        style.map("Treeview", background=[("selected", PRIMARY)], foreground=[("selected", "white")])
        style.configure("TProgressbar", thickness=8)

        # layout: sidebar | content
        root = ttk.Frame(self, style="Content.TFrame")
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        self.status = StatusBar(self)
        self.status.pack(side="bottom", fill="x")

        sidebar = Sidebar(root, self.show_tool)
        sidebar.grid(row=0, column=0, sticky="nsw")

        self.content = ttk.Frame(root, style="Content.TFrame")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)

        # frames
        self.frames = {}
        self.frames[CMSTools.CONNECT_TO_CMS.value] = ConnectFrame(self.content, self.status)
        self.frames[CMSTools.PATH_BUILDER.value] = PathBuilderFrame(self.content, self.status)
        self.frames[CMSTools.INTERACTIVE_PATH_BUILDER.value] = InteractiveBuilderFrame(self.content, self.status)
        self.frames[CMSTools.BULK_UPLOADER.value] = BulkUploaderFrame(self.content, self.status)
        for f in self.frames.values():
            f.grid(row=0, column=0, sticky="nsew")

        # menu
        menubar = tk.Menu(self)
        app_menu = tk.Menu(menubar, tearoff=0)
        app_menu.add_command(label="Refresh VPN/CMS status (F5)", command=self.status.refresh)
        app_menu.add_separator()
        app_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=app_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", f"{APP_NAME}\nHealth Canada — NHPD\n\n• Connect to CMS (Z:)\n• Build CMS paths\n• Bulk upload with validation\n\nTip: Run Dry run before Upload.", parent=self))
        menubar.add_cascade(label="Help", menu=help_menu)
        self.configure(menu=menubar)
        self.bind("<F5>", lambda e: self.status.refresh())

        sidebar.select(CMSTools.CONNECT_TO_CMS.value)

        # polish: set icon if available, center
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2 - 20
        self.geometry(f"+{x}+{y}")

    def show_tool(self, key):
        frame = self.frames.get(key)
        if frame:
            frame.tkraise()
            self.status.set_message(f"{key} — ready")


def main():
    app = CMSApp()
    app.mainloop()

if __name__ == "__main__":
    main()
