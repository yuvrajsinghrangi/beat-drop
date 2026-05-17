#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║         BEAT DROP - Music Downloader             ║
║         Built by Yuvraj Singh Rangi              ║
║         LinkedIn: yuvrajsinghrangi               ║
╚══════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path


# ─── Color Palette ───────────────────────────────
BG_DARK      = "#0d0d0d"
BG_CARD      = "#141414"
BG_INPUT     = "#1a1a1a"
BG_HOVER     = "#1f1f1f"
ACCENT       = "#00e5ff"
ACCENT_DIM   = "#009ab5"
ACCENT_GLOW  = "#00e5ff22"
TEXT_PRIMARY = "#f0f0f0"
TEXT_MUTED   = "#666666"
TEXT_DIM     = "#444444"
SUCCESS      = "#00e676"
WARNING      = "#ffab40"
ERROR        = "#ff5252"
BORDER       = "#222222"


def check_dependencies():
    """Check if yt-dlp and ffmpeg are available."""
    missing = []
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append("yt-dlp")
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append("ffmpeg")
    return missing


class SearchResult:
    def __init__(self, title, duration, uploader, url, thumbnail=""):
        self.title = title
        self.duration = duration
        self.uploader = uploader
        self.url = url
        self.thumbnail = thumbnail


class BeatDropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Beat Drop — Music Downloader")
        self.root.geometry("860x700")
        self.root.minsize(760, 600)
        self.root.configure(bg=BG_DARK)

        # State
        self.search_results = []
        self.selected_index = tk.IntVar(value=-1)
        self.download_folder = tk.StringVar(value=str(Path.home() / "Music"))
        self.quality = tk.StringVar(value="320")
        self.source = tk.StringVar(value="youtube")
        self.is_searching = False
        self.is_downloading = False
        self.history = []
        self.current_process = None

        # Fonts
        self.font_title   = ("Courier New", 13, "bold")
        self.font_heading  = ("Courier New", 11, "bold")
        self.font_body     = ("Courier New", 10)
        self.font_small    = ("Courier New", 9)
        self.font_mono     = ("Courier New", 9)
        self.font_logo     = ("Courier New", 22, "bold")

        self._setup_styles()
        self._build_ui()
        self._check_deps_on_start()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Custom.TCombobox",
            fieldbackground=BG_INPUT,
            background=BG_INPUT,
            foreground=TEXT_PRIMARY,
            selectbackground=ACCENT_DIM,
            selectforeground=BG_DARK,
            bordercolor=BORDER,
            arrowcolor=ACCENT,
            relief="flat",
            padding=6
        )
        style.map("Custom.TCombobox",
            fieldbackground=[("readonly", BG_INPUT)],
            selectbackground=[("readonly", ACCENT_DIM)]
        )

        style.configure("Custom.Horizontal.TProgressbar",
            troughcolor=BG_INPUT,
            background=ACCENT,
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=ACCENT_DIM,
            thickness=6
        )

    def _check_deps_on_start(self):
        missing = check_dependencies()
        if missing:
            msg = "Missing dependencies:\n\n"
            for dep in missing:
                if dep == "yt-dlp":
                    msg += "  • yt-dlp  →  pip install yt-dlp\n"
                elif dep == "ffmpeg":
                    msg += "  • ffmpeg  →  sudo apt install ffmpeg\n"
            msg += "\nInstall them and restart the app."
            self.root.after(500, lambda: messagebox.showwarning("Setup Required", msg))

    def _build_ui(self):
        # ── Header ──────────────────────────────────
        header = tk.Frame(self.root, bg=BG_DARK, pady=0)
        header.pack(fill="x", padx=0, pady=0)

        # Top bar with logo
        topbar = tk.Frame(header, bg=BG_CARD, pady=14)
        topbar.pack(fill="x")

        logo_frame = tk.Frame(topbar, bg=BG_CARD)
        logo_frame.pack(side="left", padx=24)

        tk.Label(logo_frame, text="◈ BEAT DROP", font=self.font_logo,
                 bg=BG_CARD, fg=ACCENT).pack(side="left")
        tk.Label(logo_frame, text="  music downloader", font=self.font_body,
                 bg=BG_CARD, fg=TEXT_MUTED).pack(side="left", pady=(6, 0))

        info_frame = tk.Frame(topbar, bg=BG_CARD)
        info_frame.pack(side="right", padx=24)

        tk.Label(info_frame, text="Yuvraj Singh Rangi", font=self.font_small,
                 bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor="e")
        tk.Label(info_frame, text="in/yuvrajsinghrangi", font=self.font_small,
                 bg=BG_CARD, fg=ACCENT).pack(anchor="e")

        # Separator line
        tk.Frame(self.root, bg=ACCENT, height=1).pack(fill="x")

        # ── Main Container ───────────────────────────
        main = tk.Frame(self.root, bg=BG_DARK)
        main.pack(fill="both", expand=True, padx=20, pady=16)

        # Left Column
        left = tk.Frame(main, bg=BG_DARK)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Right Column (settings)
        right = tk.Frame(main, bg=BG_DARK, width=200)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        self._build_search_section(left)
        self._build_results_section(left)
        self._build_progress_section(left)
        self._build_settings_panel(right)

        # ── Footer ───────────────────────────────────
        footer = tk.Frame(self.root, bg=BG_CARD, pady=8)
        footer.pack(fill="x", side="bottom")
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", side="bottom")

        self.status_var = tk.StringVar(value="Ready. Search for a song to begin.")
        tk.Label(footer, textvariable=self.status_var, font=self.font_small,
                 bg=BG_CARD, fg=TEXT_MUTED, anchor="w").pack(side="left", padx=20)

        tk.Label(footer, text="yt-dlp + ffmpeg", font=self.font_small,
                 bg=BG_CARD, fg=TEXT_DIM).pack(side="right", padx=20)

    def _build_search_section(self, parent):
        section = tk.Frame(parent, bg=BG_DARK)
        section.pack(fill="x", pady=(0, 12))

        tk.Label(section, text="SEARCH", font=self.font_heading,
                 bg=BG_DARK, fg=ACCENT).pack(anchor="w", pady=(0, 6))

        row = tk.Frame(section, bg=BG_DARK)
        row.pack(fill="x")

        # Search entry with border effect
        entry_wrap = tk.Frame(row, bg=BORDER, bd=0)
        entry_wrap.pack(side="left", fill="x", expand=True, padx=(0, 8))

        inner = tk.Frame(entry_wrap, bg=BG_INPUT, padx=10, pady=0)
        inner.pack(fill="both", padx=1, pady=1)

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(inner, textvariable=self.search_var,
            font=("Courier New", 11), bg=BG_INPUT, fg=TEXT_PRIMARY,
            insertbackground=ACCENT, relief="flat", bd=0,
            highlightthickness=0)
        self.search_entry.pack(fill="x", ipady=8)
        self.search_entry.bind("<Return>", lambda e: self._do_search())
        self.search_entry.bind("<FocusIn>",
            lambda e: entry_wrap.configure(bg=ACCENT))
        self.search_entry.bind("<FocusOut>",
            lambda e: entry_wrap.configure(bg=BORDER))
        self.search_entry.insert(0, "e.g. Sidhu Moosewala 295")
        self.search_entry.config(fg=TEXT_MUTED)

        def on_focus_in(e):
            entry_wrap.configure(bg=ACCENT)
            if self.search_entry.get() == "e.g. Sidhu Moosewala 295":
                self.search_entry.delete(0, "end")
                self.search_entry.config(fg=TEXT_PRIMARY)

        def on_focus_out(e):
            entry_wrap.configure(bg=BORDER)
            if not self.search_entry.get():
                self.search_entry.insert(0, "e.g. Sidhu Moosewala 295")
                self.search_entry.config(fg=TEXT_MUTED)

        self.search_entry.bind("<FocusIn>", on_focus_in)
        self.search_entry.bind("<FocusOut>", on_focus_out)

        self.search_btn = tk.Button(row, text="SEARCH",
            font=self.font_heading, bg=ACCENT, fg=BG_DARK,
            activebackground=ACCENT_DIM, activeforeground=BG_DARK,
            relief="flat", bd=0, padx=20, pady=10, cursor="hand2",
            command=self._do_search)
        self.search_btn.pack(side="left")

        # Source chips
        chip_row = tk.Frame(section, bg=BG_DARK)
        chip_row.pack(fill="x", pady=(8, 0))

        tk.Label(chip_row, text="Source:", font=self.font_small,
                 bg=BG_DARK, fg=TEXT_MUTED).pack(side="left", padx=(0, 8))

        sources = [
            ("YouTube",       "youtube"),
            ("YouTube Music", "ytmusic"),
            ("JioSaavn",      "jiosaavn"),
            ("SoundCloud",    "soundcloud"),
        ]
        self.chip_buttons = {}
        for label, val in sources:
            btn = tk.Button(chip_row, text=label, font=self.font_small,
                bg=ACCENT if val == "youtube" else BG_INPUT,
                fg=BG_DARK if val == "youtube" else TEXT_MUTED,
                activebackground=ACCENT_DIM, activeforeground=BG_DARK,
                relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                command=lambda v=val: self._select_source(v))
            btn.pack(side="left", padx=(0, 4))
            self.chip_buttons[val] = btn

    def _select_source(self, val):
        self.source.set(val)
        for k, btn in self.chip_buttons.items():
            if k == val:
                btn.configure(bg=ACCENT, fg=BG_DARK)
            else:
                btn.configure(bg=BG_INPUT, fg=TEXT_MUTED)

    def _build_results_section(self, parent):
        section = tk.Frame(parent, bg=BG_DARK)
        section.pack(fill="both", expand=True, pady=(0, 12))

        hdr = tk.Frame(section, bg=BG_DARK)
        hdr.pack(fill="x", pady=(0, 6))
        tk.Label(hdr, text="RESULTS", font=self.font_heading,
                 bg=BG_DARK, fg=ACCENT).pack(side="left")
        self.result_count_var = tk.StringVar(value="")
        tk.Label(hdr, textvariable=self.result_count_var, font=self.font_small,
                 bg=BG_DARK, fg=TEXT_MUTED).pack(side="left", padx=8, pady=(2, 0))

        # Results listbox
        list_wrap = tk.Frame(section, bg=BORDER)
        list_wrap.pack(fill="both", expand=True)

        inner = tk.Frame(list_wrap, bg=BG_CARD)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        scrollbar = tk.Scrollbar(inner, bg=BG_CARD, troughcolor=BG_INPUT,
                                  activebackground=ACCENT, relief="flat", bd=0)
        scrollbar.pack(side="right", fill="y")

        self.results_list = tk.Listbox(inner,
            font=("Courier New", 10),
            bg=BG_CARD, fg=TEXT_PRIMARY,
            selectbackground=ACCENT_DIM, selectforeground=BG_DARK,
            activestyle="none",
            relief="flat", bd=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
            cursor="hand2",
            height=8)
        self.results_list.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        scrollbar.config(command=self.results_list.yview)
        self.results_list.bind("<<ListboxSelect>>", self._on_result_select)
        self.results_list.bind("<Double-Button-1>", lambda e: self._start_download())

        # Selected info bar
        self.sel_info_var = tk.StringVar(value="No song selected")
        sel_bar = tk.Frame(section, bg=BG_INPUT, pady=6, padx=10)
        sel_bar.pack(fill="x", pady=(4, 0))
        tk.Label(sel_bar, textvariable=self.sel_info_var, font=self.font_small,
                 bg=BG_INPUT, fg=TEXT_MUTED, anchor="w").pack(fill="x")

        # Download button
        self.dl_btn = tk.Button(section, text="⬇  DOWNLOAD SELECTED",
            font=self.font_heading, bg=BG_INPUT, fg=TEXT_DIM,
            activebackground=SUCCESS, activeforeground=BG_DARK,
            relief="flat", bd=0, pady=12, cursor="hand2",
            command=self._start_download, state="disabled")
        self.dl_btn.pack(fill="x", pady=(8, 0))

    def _build_progress_section(self, parent):
        section = tk.Frame(parent, bg=BG_DARK)
        section.pack(fill="x", pady=(0, 8))

        tk.Label(section, text="PROGRESS", font=self.font_heading,
                 bg=BG_DARK, fg=ACCENT).pack(anchor="w", pady=(0, 6))

        prog_wrap = tk.Frame(section, bg=BORDER)
        prog_wrap.pack(fill="x")
        prog_inner = tk.Frame(prog_wrap, bg=BG_CARD, pady=10, padx=12)
        prog_inner.pack(fill="x", padx=1, pady=1)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(prog_inner,
            variable=self.progress_var,
            style="Custom.Horizontal.TProgressbar",
            maximum=100, length=400)
        self.progress_bar.pack(fill="x", pady=(0, 6))

        info_row = tk.Frame(prog_inner, bg=BG_CARD)
        info_row.pack(fill="x")

        self.prog_label_var = tk.StringVar(value="Idle")
        tk.Label(info_row, textvariable=self.prog_label_var,
                 font=self.font_small, bg=BG_CARD, fg=TEXT_MUTED,
                 anchor="w").pack(side="left")

        self.speed_var = tk.StringVar(value="")
        tk.Label(info_row, textvariable=self.speed_var,
                 font=self.font_small, bg=BG_CARD, fg=ACCENT,
                 anchor="e").pack(side="right")

        # History
        hist_hdr = tk.Frame(section, bg=BG_DARK)
        hist_hdr.pack(fill="x", pady=(10, 4))
        tk.Label(hist_hdr, text="HISTORY", font=self.font_heading,
                 bg=BG_DARK, fg=ACCENT).pack(side="left")

        tk.Button(hist_hdr, text="clear", font=self.font_small,
            bg=BG_DARK, fg=TEXT_DIM, activebackground=BG_INPUT,
            activeforeground=TEXT_MUTED, relief="flat", bd=0,
            cursor="hand2", command=self._clear_history).pack(side="right")

        hist_wrap = tk.Frame(section, bg=BORDER)
        hist_wrap.pack(fill="x")
        hist_inner = tk.Frame(hist_wrap, bg=BG_CARD)
        hist_inner.pack(fill="x", padx=1, pady=1)

        hist_scroll = tk.Scrollbar(hist_inner, bg=BG_CARD, troughcolor=BG_INPUT,
                                    activebackground=ACCENT, relief="flat", bd=0)
        hist_scroll.pack(side="right", fill="y")

        self.history_box = tk.Listbox(hist_inner,
            font=self.font_mono, bg=BG_CARD, fg=TEXT_MUTED,
            selectbackground=BG_HOVER, selectforeground=TEXT_PRIMARY,
            activestyle="none", relief="flat", bd=0,
            highlightthickness=0, height=3,
            yscrollcommand=hist_scroll.set)
        self.history_box.pack(side="left", fill="both", expand=True, padx=8, pady=4)
        hist_scroll.config(command=self.history_box.yview)

    def _build_settings_panel(self, parent):
        tk.Label(parent, text="SETTINGS", font=self.font_heading,
                 bg=BG_DARK, fg=ACCENT).pack(anchor="w", pady=(0, 10))

        # Quality
        self._settings_label(parent, "QUALITY")
        qualities = [("320 kbps", "320"), ("192 kbps", "192"), ("128 kbps", "128")]
        self.qual_btns = {}
        for label, val in qualities:
            b = tk.Button(parent, text=label, font=self.font_small,
                bg=ACCENT if val == "320" else BG_INPUT,
                fg=BG_DARK if val == "320" else TEXT_MUTED,
                activebackground=ACCENT_DIM, activeforeground=BG_DARK,
                relief="flat", bd=0, pady=6, cursor="hand2",
                command=lambda v=val: self._select_quality(v))
            b.pack(fill="x", pady=2)
            self.qual_btns[val] = b

        # Format
        self._settings_label(parent, "FORMAT")
        formats = [("MP3", "mp3"), ("M4A", "m4a"), ("FLAC", "flac"), ("WAV", "wav")]
        self.format_var = tk.StringVar(value="mp3")
        self.fmt_btns = {}
        for label, val in formats:
            b = tk.Button(parent, text=label, font=self.font_small,
                bg=ACCENT if val == "mp3" else BG_INPUT,
                fg=BG_DARK if val == "mp3" else TEXT_MUTED,
                activebackground=ACCENT_DIM, activeforeground=BG_DARK,
                relief="flat", bd=0, pady=6, cursor="hand2",
                command=lambda v=val: self._select_format(v))
            b.pack(fill="x", pady=2)
            self.fmt_btns[val] = b

        # Download folder
        self._settings_label(parent, "SAVE TO")
        folder_wrap = tk.Frame(parent, bg=BORDER)
        folder_wrap.pack(fill="x", pady=2)
        folder_inner = tk.Frame(folder_wrap, bg=BG_INPUT)
        folder_inner.pack(fill="x", padx=1, pady=1)

        self.folder_label = tk.Label(folder_inner,
            text=self._short_path(self.download_folder.get()),
            font=self.font_small, bg=BG_INPUT, fg=TEXT_MUTED,
            anchor="w", wraplength=160)
        self.folder_label.pack(fill="x", padx=6, pady=4)

        tk.Button(parent, text="Browse...", font=self.font_small,
            bg=BG_INPUT, fg=TEXT_MUTED,
            activebackground=BG_HOVER, activeforeground=TEXT_PRIMARY,
            relief="flat", bd=0, pady=6, cursor="hand2",
            command=self._browse_folder).pack(fill="x", pady=(2, 12))

        # Results count
        self._settings_label(parent, "MAX RESULTS")
        self.max_results_var = tk.StringVar(value="5")
        max_wrap = tk.Frame(parent, bg=BORDER)
        max_wrap.pack(fill="x", pady=2)
        max_inner = tk.Frame(max_wrap, bg=BG_INPUT)
        max_inner.pack(fill="x", padx=1, pady=1)
        tk.Entry(max_inner, textvariable=self.max_results_var,
            font=self.font_small, bg=BG_INPUT, fg=TEXT_PRIMARY,
            insertbackground=ACCENT, relief="flat", bd=0,
            highlightthickness=0).pack(fill="x", ipady=5, padx=6)

        # Stop button
        tk.Frame(parent, bg=BG_DARK, height=10).pack()
        self.stop_btn = tk.Button(parent, text="■ STOP",
            font=self.font_heading, bg=ERROR, fg="white",
            activebackground="#cc0000", activeforeground="white",
            relief="flat", bd=0, pady=8, cursor="hand2",
            command=self._stop, state="disabled")
        self.stop_btn.pack(fill="x", pady=2)

    def _settings_label(self, parent, text):
        tk.Label(parent, text=text, font=self.font_small,
                 bg=BG_DARK, fg=TEXT_DIM).pack(anchor="w", pady=(10, 2))

    def _select_quality(self, val):
        self.quality.set(val)
        for k, b in self.qual_btns.items():
            b.configure(bg=ACCENT if k == val else BG_INPUT,
                        fg=BG_DARK if k == val else TEXT_MUTED)

    def _select_format(self, val):
        self.format_var.set(val)
        for k, b in self.fmt_btns.items():
            b.configure(bg=ACCENT if k == val else BG_INPUT,
                        fg=BG_DARK if k == val else TEXT_MUTED)

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_folder.get())
        if folder:
            self.download_folder.set(folder)
            self.folder_label.configure(text=self._short_path(folder))

    def _short_path(self, path):
        home = str(Path.home())
        if path.startswith(home):
            return "~" + path[len(home):]
        return path[-25:] if len(path) > 25 else path

    def _on_result_select(self, event):
        sel = self.results_list.curselection()
        if sel and self.search_results:
            idx = sel[0]
            if idx < len(self.search_results):
                r = self.search_results[idx]
                self.sel_info_var.set(f"{r.uploader}  •  {r.duration}")
                self.dl_btn.configure(bg=SUCCESS, fg=BG_DARK, state="normal")

    def _do_search(self):
        query = self.search_var.get().strip()
        if not query or query == "e.g. Sidhu Moosewala 295":
            messagebox.showwarning("Empty Query", "Please enter a song name.")
            return
        if self.is_searching or self.is_downloading:
            return

        self.is_searching = True
        self.search_btn.configure(text="SEARCHING...", state="disabled",
                                  bg=ACCENT_DIM)
        self.results_list.delete(0, "end")
        self.search_results.clear()
        self.result_count_var.set("")
        self.sel_info_var.set("Searching...")
        self.dl_btn.configure(bg=BG_INPUT, fg=TEXT_DIM, state="disabled")
        self._set_status(f"Searching: {query}")

        thread = threading.Thread(target=self._search_thread, args=(query,), daemon=True)
        thread.start()

    def _build_search_url(self, query):
        src = self.source.get()
        max_r = self.max_results_var.get().strip() or "5"
        try:
            max_r = max(1, min(int(max_r), 15))
        except ValueError:
            max_r = 5

        if src == "youtube":
            return f"ytsearch{max_r}:{query}", max_r
        elif src == "ytmusic":
            return f"https://music.youtube.com/search?q={query.replace(' ', '+')}", max_r
        elif src == "jiosaavn":
            return f"ytsearch{max_r}:{query} site:jiosaavn", max_r
        elif src == "soundcloud":
            return f"scsearch{max_r}:{query}", max_r
        return f"ytsearch{max_r}:{query}", max_r

    def _search_thread(self, query):
        try:
            search_url, max_r = self._build_search_url(query)
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-playlist",
                "--flat-playlist",
                "--no-warnings",
                "--quiet",
                search_url
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            results = []
            if proc.returncode == 0 and proc.stdout.strip():
                for line in proc.stdout.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        title = data.get("title", "Unknown Title")
                        duration = data.get("duration_string") or self._fmt_duration(data.get("duration", 0))
                        uploader = data.get("uploader") or data.get("channel") or "Unknown"
                        url = data.get("url") or data.get("webpage_url") or data.get("id", "")
                        results.append(SearchResult(title, duration, uploader, url))
                    except (json.JSONDecodeError, KeyError):
                        continue

            self.root.after(0, lambda: self._update_results(results))
        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self._search_error("Search timed out. Try again."))
        except Exception as ex:
            self.root.after(0, lambda: self._search_error(str(ex)))

    def _fmt_duration(self, secs):
        try:
            secs = int(secs)
            return f"{secs // 60}:{secs % 60:02d}"
        except Exception:
            return "?:??"

    def _update_results(self, results):
        self.is_searching = False
        self.search_btn.configure(text="SEARCH", state="normal", bg=ACCENT)

        if not results:
            self.sel_info_var.set("No results found. Try a different query.")
            self.result_count_var.set("(0 results)")
            self._set_status("No results found.")
            return

        self.search_results = results
        self.result_count_var.set(f"({len(results)} results)")

        for i, r in enumerate(results):
            title_short = r.title[:60] + "…" if len(r.title) > 60 else r.title
            dur = r.duration if r.duration else "?"
            line = f"  {i+1:02d}  {title_short:<63}  [{dur}]"
            self.results_list.insert("end", line)
            self.results_list.itemconfig(i, fg=TEXT_PRIMARY if i % 2 == 0 else "#cccccc")

        self.sel_info_var.set("← Select a result, then click DOWNLOAD")
        self._set_status(f"Found {len(results)} results for '{self.search_entry.get()}'")

    def _search_error(self, msg):
        self.is_searching = False
        self.search_btn.configure(text="SEARCH", state="normal", bg=ACCENT)
        self.sel_info_var.set(f"Error: {msg}")
        self._set_status(f"Search error: {msg}")

    def _start_download(self):
        sel = self.results_list.curselection()
        if not sel or not self.search_results:
            messagebox.showwarning("No Selection", "Please select a song first.")
            return
        idx = sel[0]
        if idx >= len(self.search_results):
            return
        if self.is_downloading:
            return

        result = self.search_results[idx]

        # Ensure output folder exists
        os.makedirs(self.download_folder.get(), exist_ok=True)

        self.is_downloading = True
        self.dl_btn.configure(state="disabled", bg=BG_INPUT, fg=TEXT_DIM,
                              text="Downloading...")
        self.stop_btn.configure(state="normal")
        self.progress_var.set(0)
        self.prog_label_var.set(f"Starting: {result.title[:40]}...")
        self.speed_var.set("")
        self._set_status(f"Downloading: {result.title[:50]}...")

        thread = threading.Thread(target=self._download_thread,
                                  args=(result,), daemon=True)
        thread.start()

    def _download_thread(self, result):
        fmt = self.format_var.get()
        quality = self.quality.get()
        outdir = self.download_folder.get()

        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", fmt,
            "--audio-quality", quality if fmt == "mp3" else "0",
            "--output", os.path.join(outdir, "%(title)s.%(ext)s"),
            "--no-playlist",
            "--newline",
            "--progress",
            result.url
        ]

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True, bufsize=1)
            self.current_process = proc

            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue

                # Parse progress
                pct_match = re.search(r'(\d+\.?\d*)%', line)
                speed_match = re.search(r'at\s+([\d.]+\s*\w+/s)', line)
                eta_match = re.search(r'ETA\s+([\d:]+)', line)

                if pct_match:
                    pct = float(pct_match.group(1))
                    speed = speed_match.group(1) if speed_match else ""
                    eta = f"ETA {eta_match.group(1)}" if eta_match else ""

                    def update_ui(p=pct, s=speed, e=eta, l=line):
                        self.progress_var.set(p)
                        self.speed_var.set(s)
                        self.prog_label_var.set(f"{p:.1f}%  {e}")
                    self.root.after(0, update_ui)

                elif "[ExtractAudio]" in line or "Destination:" in line:
                    def update_conv(l=line):
                        self.prog_label_var.set("Converting to audio...")
                        self.speed_var.set("ffmpeg")
                    self.root.after(0, update_conv)

            proc.wait()
            if proc.returncode == 0:
                self.root.after(0, lambda: self._download_done(result, True))
            else:
                self.root.after(0, lambda: self._download_done(result, False,
                    "yt-dlp returned an error."))
        except Exception as ex:
            self.root.after(0, lambda: self._download_done(result, False, str(ex)))
        finally:
            self.current_process = None

    def _download_done(self, result, success, error=""):
        self.is_downloading = False
        self.stop_btn.configure(state="disabled")
        self.dl_btn.configure(state="normal", text="⬇  DOWNLOAD SELECTED",
                              bg=SUCCESS, fg=BG_DARK)

        if success:
            self.progress_var.set(100)
            self.prog_label_var.set("Download complete!")
            self.speed_var.set("✓")
            self._set_status(f"Saved: {result.title[:50]}")

            ts = datetime.now().strftime("%H:%M:%S")
            fmt = self.format_var.get().upper()
            entry = f"  ✓  [{ts}]  {result.title[:45]}  [{fmt}]"
            self.history_box.insert(0, entry)
            self.history_box.itemconfig(0, fg=SUCCESS)
            self.history.append(result.title)
        else:
            self.progress_var.set(0)
            self.prog_label_var.set(f"Failed: {error}")
            self.speed_var.set("✗")
            self._set_status(f"Download failed: {error}")

            ts = datetime.now().strftime("%H:%M:%S")
            entry = f"  ✗  [{ts}]  {result.title[:45]}"
            self.history_box.insert(0, entry)
            self.history_box.itemconfig(0, fg=ERROR)

    def _stop(self):
        if self.current_process:
            self.current_process.terminate()
        self.is_downloading = False
        self.is_searching = False
        self.stop_btn.configure(state="disabled")
        self.dl_btn.configure(state="normal", bg=SUCCESS, fg=BG_DARK,
                              text="⬇  DOWNLOAD SELECTED")
        self.search_btn.configure(text="SEARCH", state="normal", bg=ACCENT)
        self.prog_label_var.set("Stopped by user.")
        self.speed_var.set("")
        self._set_status("Stopped.")

    def _clear_history(self):
        self.history_box.delete(0, "end")
        self.history.clear()

    def _set_status(self, msg):
        self.status_var.set(msg)


def main():
    root = tk.Tk()
    root.configure(bg=BG_DARK)

    # Try to set icon / taskbar title
    try:
        root.iconbitmap("")
    except Exception:
        pass

    app = BeatDropApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
