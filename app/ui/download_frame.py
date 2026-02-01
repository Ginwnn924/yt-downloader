"""
Download Frame - URL input, just sends info to progress frame
"""

import customtkinter as ctk
from tkinter import filedialog
from typing import Callable, Optional
from pathlib import Path

from .theme import DARK, LIGHT, font, FONT_SIZE_SM, FONT_SIZE_MD, PAD_SM, PAD_MD, PAD_LG, PAD_XL


class DownloadFrame(ctk.CTkFrame):
    """Download controls - URL input and options."""
    
    def __init__(self, parent, on_download=None, on_load_url=None):
        self._mode = "dark"
        t = DARK
        
        super().__init__(parent, fg_color=t["bg_card"], corner_radius=12)
        
        self.on_download = on_download
        self.on_load_url = on_load_url
        self._output = str(Path.home() / "Downloads")
        
        # Pending items count (items added to progress but not downloading)
        self._pending_count = 0
        
        self.grid_columnconfigure(0, weight=1)
        
        self._build_url_section()
        self._build_options_section()
        self._build_download_button()
    
    def _build_url_section(self):
        """URL input with Load button."""
        t = DARK if self._mode == "dark" else LIGHT
        
        sec = ctk.CTkFrame(self, fg_color="transparent")
        sec.grid(row=0, column=0, sticky="ew", padx=PAD_LG, pady=(PAD_LG, PAD_SM))
        sec.grid_columnconfigure(0, weight=1)
        self.url_sec = sec
        
        self.url_lbl = ctk.CTkLabel(
            sec, text="Video / Playlist URL",
            font=font(FONT_SIZE_SM, bold=True),
            text_color=t["text_dim"], anchor="w"
        )
        self.url_lbl.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, PAD_SM))
        
        row = ctk.CTkFrame(sec, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew")
        row.grid_columnconfigure(0, weight=1)
        
        self.url_entry = ctk.CTkEntry(
            row,
            placeholder_text="https://youtube.com/watch?v=... or playlist",
            height=40,
            font=font(FONT_SIZE_SM),
            fg_color=t["bg_input"],
            border_color=t["border"],
            border_width=1,
            text_color=t["text"],
            placeholder_text_color=t["text_muted"],
            corner_radius=8
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, PAD_MD))
        
        self.load_btn = ctk.CTkButton(
            row,
            text="Load",
            width=70,
            height=40,
            font=font(FONT_SIZE_SM, bold=True),
            fg_color=t["blue"],
            hover_color=t["blue_hover"],
            text_color="#ffffff",
            corner_radius=8,
            command=self._on_load
        )
        self.load_btn.grid(row=0, column=1)
        
        self.status = ctk.CTkLabel(
            sec, text="",
            font=font(FONT_SIZE_SM),
            text_color=t["text_muted"], anchor="w"
        )
        self.status.grid(row=2, column=0, sticky="w", pady=(PAD_SM, 0))
    
    def _build_options_section(self):
        """Save location and quality."""
        t = DARK if self._mode == "dark" else LIGHT
        
        sec = ctk.CTkFrame(self, fg_color="transparent")
        sec.grid(row=1, column=0, sticky="ew", padx=PAD_LG, pady=PAD_SM)
        sec.grid_columnconfigure(1, weight=1)
        self.opt_sec = sec
        
        # Save to
        self.out_lbl = ctk.CTkLabel(
            sec, text="Save to",
            font=font(FONT_SIZE_SM, bold=True),
            text_color=t["text_dim"], anchor="w"
        )
        self.out_lbl.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, PAD_SM))
        
        self.out_path = ctk.CTkLabel(
            sec,
            text=self._shorten(self._output),
            font=font(FONT_SIZE_SM),
            fg_color=t["bg_input"],
            text_color=t["text"],
            corner_radius=6,
            height=36,
            anchor="w",
            padx=PAD_SM
        )
        self.out_path.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, PAD_MD))
        
        self.browse_btn = ctk.CTkButton(
            sec, text="Browse",
            width=70, height=36,
            font=font(FONT_SIZE_SM),
            fg_color=t["bg_input"],
            hover_color=t["bg_hover"],
            text_color=t["text"],
            corner_radius=6,
            command=self._browse
        )
        self.browse_btn.grid(row=1, column=2)
        
        # Quality
        self.qual_lbl = ctk.CTkLabel(
            sec, text="Quality",
            font=font(FONT_SIZE_SM, bold=True),
            text_color=t["text_dim"], anchor="w"
        )
        self.qual_lbl.grid(row=2, column=0, sticky="w", pady=(PAD_MD, PAD_SM))
        
        quality_opts = ["2160p (4K)", "1440p", "1080p", "720p", "480p", "360p"]
        self.qual_var = ctk.StringVar(value="1080p")
        self.qual_menu = ctk.CTkOptionMenu(
            sec,
            values=quality_opts,
            variable=self.qual_var,
            width=180, height=36,
            font=font(FONT_SIZE_SM),
            fg_color=t["bg_input"],
            button_color=t["blue"],
            button_hover_color=t["blue_hover"],
            dropdown_fg_color=t["bg_card"],
            dropdown_hover_color=t["bg_hover"],
            text_color=t["text"],
            corner_radius=6
        )
        self.qual_menu.grid(row=2, column=1, sticky="w", padx=(PAD_MD, 0), pady=(PAD_MD, 0))
    
    def _build_download_button(self):
        """Download button."""
        t = DARK if self._mode == "dark" else LIGHT
        
        self.dl_btn = ctk.CTkButton(
            self,
            text="⬇  Download",
            height=46,
            font=font(FONT_SIZE_MD, bold=True),
            fg_color=t["blue"],
            hover_color=t["blue_hover"],
            text_color="#ffffff",
            corner_radius=10,
            state="disabled",
            command=self._on_download
        )
        self.dl_btn.grid(row=2, column=0, sticky="ew", padx=PAD_LG, pady=PAD_LG)
    
    def _shorten(self, path: str, max_len: int = 40) -> str:
        return path if len(path) <= max_len else "..." + path[-(max_len - 3):]
    
    def _on_load(self):
        url = self.url_entry.get().strip()
        if not url:
            self._set_status("Enter a URL first", "red")
            return
        if not url.startswith(("http://", "https://")):
            self._set_status("Invalid URL", "red")
            return
        
        self.load_btn.configure(text="...", state="disabled")
        self._set_status("Loading...", None)
        
        if self.on_load_url:
            self.on_load_url(url)
    
    def _set_status(self, msg: str, color: str | None):
        t = DARK if self._mode == "dark" else LIGHT
        c = t["red"] if color == "red" else (t["green"] if color == "green" else t["text_muted"])
        self.status.configure(text=msg, text_color=c)
    
    def _browse(self):
        path = filedialog.askdirectory(initialdir=self._output)
        if path:
            self._output = path
            self.out_path.configure(text=self._shorten(path))
    
    def on_video_loaded(self, added_count: int = 1):
        """Called when video(s) added to progress as pending."""
        self.load_btn.configure(text="Load", state="normal")
        self._pending_count += added_count
        self._set_status(f"✓ Added {added_count} to queue", "green")
        self.url_entry.delete(0, "end")
        self._update_download_btn()
    
    def on_load_error(self, error: str):
        """Called when loading failed."""
        self.load_btn.configure(text="Load", state="normal")
        self._set_status(f"Error: {error[:50]}", "red")
        
        # Show error popup
        from tkinter import messagebox
        
        # Check if it's a 403 error suggesting yt-dlp update
        if "403" in error or "Forbidden" in error or "update yt-dlp" in error.lower():
            result = messagebox.askyesno(
                "Update Required",
                "HTTP 403 Forbidden error detected.\n\n"
                "This usually means yt-dlp needs to be updated.\n\n"
                "Would you like to update yt-dlp now?",
                icon="warning"
            )
            if result:
                # Trigger update - find main window and call update
                self._trigger_update()
        else:
            messagebox.showerror("Error", error)
    
    def _trigger_update(self):
        """Trigger yt-dlp update from parent window."""
        # Walk up parent tree to find MainWindow
        parent = self.master
        while parent:
            if hasattr(parent, 'master') and hasattr(parent.master, 'main'):
                # Found App, get main window
                main = parent.master.main
                if hasattr(main, '_do_update'):
                    main._do_update()
                    return
            if hasattr(parent, '_do_update'):
                parent._do_update()
                return
            parent = getattr(parent, 'master', None)
    
    def _update_download_btn(self):
        if self._pending_count > 0:
            self.dl_btn.configure(text=f"⬇  Download ({self._pending_count})", state="normal")
        else:
            self.dl_btn.configure(text="⬇  Download", state="disabled")
    
    def set_pending_count(self, count: int):
        """Update pending count from main window."""
        self._pending_count = count
        self._update_download_btn()
    
    def get_quality_height(self) -> int:
        """Get selected quality as height."""
        sel = self.qual_var.get()
        try:
            import re
            match = re.search(r'(\d+)p', sel)
            return int(match.group(1)) if match else 1080
        except:
            return 1080
    
    def get_output_dir(self) -> str:
        return self._output
    
    def _on_download(self):
        if self._pending_count == 0:
            return
        
        if self.on_download:
            self.on_download()
    
    def set_downloading(self, active: bool):
        if active:
            self.dl_btn.configure(text="Downloading...", state="disabled")
            self.load_btn.configure(state="disabled")
        else:
            self.load_btn.configure(state="normal")
            self._update_download_btn()
    
    def update_theme(self, mode: str):
        self._mode = mode
        t = DARK if mode == "dark" else LIGHT
        
        self.configure(fg_color=t["bg_card"])
        
        # URL section
        self.url_lbl.configure(text_color=t["text_dim"])
        self.url_entry.configure(
            fg_color=t["bg_input"],
            border_color=t["border"],
            text_color=t["text"],
            placeholder_text_color=t["text_muted"]
        )
        self.load_btn.configure(fg_color=t["blue"], hover_color=t["blue_hover"])
        self.status.configure(text_color=t["text_muted"])
        
        # Options section
        self.out_lbl.configure(text_color=t["text_dim"])
        self.out_path.configure(fg_color=t["bg_input"], text_color=t["text"])
        self.browse_btn.configure(fg_color=t["bg_input"], hover_color=t["bg_hover"], text_color=t["text"])
        self.qual_lbl.configure(text_color=t["text_dim"])
        self.qual_menu.configure(
            fg_color=t["bg_input"],
            button_color=t["blue"],
            button_hover_color=t["blue_hover"],
            dropdown_fg_color=t["bg_card"],
            dropdown_hover_color=t["bg_hover"],
            text_color=t["text"]
        )
        
        # Download button
        self.dl_btn.configure(fg_color=t["blue"], hover_color=t["blue_hover"])
