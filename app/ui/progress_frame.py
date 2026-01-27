"""
Progress Frame - Download list with proper per-video tracking
"""

import customtkinter as ctk
from typing import Callable, Optional
import threading
import io

from .theme import DARK, LIGHT, font, FONT_SIZE_SM, FONT_SIZE_MD, PAD_SM, PAD_MD, PAD_LG

try:
    from PIL import Image
    import urllib.request
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ProgressFrame(ctk.CTkFrame):
    """Download progress list with neon styling."""
    
    def __init__(self, parent, on_pause=None, on_resume=None, on_cancel=None, on_retry=None):
        self._mode = "dark"
        t = DARK
        
        super().__init__(parent, fg_color=t["bg_card"], corner_radius=12)
        
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_cancel = on_cancel
        self.on_retry = on_retry
        
        self._downloads = {}  # download_id -> DownloadItem
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._build_header()
        self._build_list()
    
    def _build_header(self):
        t = DARK if self._mode == "dark" else LIGHT
        
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=PAD_LG, pady=(PAD_LG, PAD_SM))
        hdr.grid_columnconfigure(0, weight=1)
        self.header = hdr
        
        self.header_title = ctk.CTkLabel(
            hdr, text="Downloads",
            font=font(FONT_SIZE_MD, bold=True),
            text_color=t["text"], anchor="w"
        )
        self.header_title.grid(row=0, column=0, sticky="w")
        
        self.clear_btn = ctk.CTkButton(
            hdr, text="Clear",
            width=60, height=28,
            font=font(FONT_SIZE_SM),
            fg_color="transparent",
            hover_color=t["bg_hover"],
            text_color=t["text_dim"],
            border_width=1,
            border_color=t["border"],
            corner_radius=6,
            command=self._clear
        )
        self.clear_btn.grid(row=0, column=1)
    
    def _build_list(self):
        t = DARK if self._mode == "dark" else LIGHT
        
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color=t["bg_input"], corner_radius=10
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=PAD_MD, pady=(0, PAD_MD))
        self.scroll.grid_columnconfigure(0, weight=1)
        
        self.empty = ctk.CTkLabel(
            self.scroll,
            text="No downloads yet\n\nLoad a video and click Download",
            font=font(FONT_SIZE_SM),
            text_color=t["text_muted"],
            justify="center"
        )
        self.empty.grid(row=0, column=0, pady=80)
    
    def add_download(self, download_id: str, title: str, url: str, thumbnail_url: str = "", thumbnail_image=None, pending: bool = False):
        """Add a new download item."""
        self.empty.grid_forget()
        
        item = DownloadItem(
            self.scroll,
            download_id=download_id,
            title=title,
            thumbnail_url=thumbnail_url,
            thumbnail_image=thumbnail_image,
            on_pause=lambda: self._fire_pause(download_id),
            on_resume=lambda: self._fire_resume(download_id),
            on_cancel=lambda: self._fire_cancel(download_id),
            on_retry=lambda: self._fire_retry(download_id),
            mode=self._mode,
            pending=pending
        )
        item.grid(row=len(self._downloads), column=0, sticky="ew", pady=(0, PAD_SM))
        
        self._downloads[download_id] = item
    
    def start_download(self, download_id: str):
        """Start a pending download."""
        if download_id in self._downloads:
            self._downloads[download_id].start_download()
    
    def get_pending_ids(self) -> list:
        """Get list of pending download IDs."""
        return [id for id, item in self._downloads.items() if item.is_pending]
    
    def update_download(self, download_id: str, percent: float, speed: str = "", eta: str = ""):
        """Update progress for specific download."""
        if download_id in self._downloads:
            self._downloads[download_id].update_progress(percent, speed, eta)
    
    def complete_download(self, download_id: str, success: bool = True, message: str = ""):
        """Mark download as complete."""
        if download_id in self._downloads:
            self._downloads[download_id].set_complete(success, message)
    
    def _fire_pause(self, id):
        if self.on_pause:
            self.on_pause(id)
        if id in self._downloads:
            self._downloads[id].set_paused(True)
    
    def _fire_resume(self, id):
        if self.on_resume:
            self.on_resume(id)
        if id in self._downloads:
            self._downloads[id].set_paused(False)
    
    def _fire_cancel(self, id):
        if self.on_cancel:
            self.on_cancel(id)
        if id in self._downloads:
            self._downloads[id].set_cancelled()
    
    def _fire_retry(self, id):
        if self.on_retry:
            self.on_retry(id)
        if id in self._downloads:
            self._downloads[id].set_retrying()
    
    def _clear(self):
        """Clear finished downloads."""
        remove = [id for id, item in self._downloads.items() if item.is_finished]
        for id in remove:
            self._downloads[id].destroy()
            del self._downloads[id]
        
        # Re-grid remaining items
        for i, item in enumerate(self._downloads.values()):
            item.grid(row=i, column=0, sticky="ew", pady=(0, PAD_SM))
        
        if not self._downloads:
            self.empty.grid(row=0, column=0, pady=80)
    
    def update_theme(self, mode: str):
        self._mode = mode
        t = DARK if mode == "dark" else LIGHT
        
        self.configure(fg_color=t["bg_card"])
        self.header_title.configure(text_color=t["text"])
        self.clear_btn.configure(
            hover_color=t["bg_hover"],
            text_color=t["text_dim"],
            border_color=t["border"]
        )
        self.scroll.configure(fg_color=t["bg_input"])
        self.empty.configure(text_color=t["text_muted"])
        
        for item in self._downloads.values():
            item.update_theme(mode)


class DownloadItem(ctk.CTkFrame):
    """Single download item with neon progress bar."""
    
    def __init__(self, parent, download_id, title, thumbnail_url="", thumbnail_image=None,
                 on_pause=None, on_resume=None, on_cancel=None, on_retry=None, mode="dark", pending=False):
        self._mode = mode
        t = DARK if mode == "dark" else LIGHT
        
        super().__init__(parent, fg_color=t["bg_card"], corner_radius=10)
        
        self.download_id = download_id
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_cancel = on_cancel
        self.on_retry = on_retry
        
        self._paused = False
        self._finished = False
        self._waiting = False
        self._pending = pending
        
        self.grid_columnconfigure(1, weight=1)
        
        # Thumbnail
        self.thumb = ctk.CTkLabel(self, text="🎬", width=72, height=40, font=ctk.CTkFont(size=18))
        self.thumb.grid(row=0, column=0, rowspan=2, padx=PAD_MD, pady=PAD_MD)
        
        if thumbnail_image:
            self.thumb.configure(image=thumbnail_image, text="")
        elif thumbnail_url:
            self._load_thumb(thumbnail_url)
        
        # Title
        t_text = title[:40] + "..." if len(title) > 40 else title
        self.title_lbl = ctk.CTkLabel(
            self, text=t_text,
            font=font(FONT_SIZE_SM, bold=True),
            text_color=t["text"], anchor="w"
        )
        self.title_lbl.grid(row=0, column=1, sticky="w", padx=(0, PAD_SM), pady=(PAD_MD, 0))
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(
            self, height=8, corner_radius=4,
            progress_color=t["neon_cyan"],
            fg_color=t["bg_input"]
        )
        self.progress.grid(row=1, column=1, sticky="ew", padx=(0, PAD_SM), pady=PAD_SM)
        self.progress.set(0)
        
        # Bottom row
        btm = ctk.CTkFrame(self, fg_color="transparent")
        btm.grid(row=2, column=0, columnspan=2, sticky="ew", padx=PAD_MD, pady=(0, PAD_MD))
        btm.grid_columnconfigure(0, weight=1)
        
        # Initial text based on pending state
        initial_text = "📥 Pending..." if pending else "⚡ Starting..."
        initial_color = t["text_dim"] if pending else t["neon_cyan"]
        
        self.stats = ctk.CTkLabel(
            btm, text=initial_text,
            font=font(FONT_SIZE_SM),
            text_color=initial_color, anchor="w"
        )
        self.stats.grid(row=0, column=0, sticky="w")
        
        btns = ctk.CTkFrame(btm, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e")
        self.btns = btns
        
        self.pause_btn = ctk.CTkButton(
            btns, text="⏸", width=32, height=28,
            font=ctk.CTkFont(size=14),
            fg_color=t["bg_input"],
            hover_color=t["neon_purple"],
            text_color=t["neon_cyan"],
            corner_radius=6,
            command=self._toggle_pause
        )
        if not pending:
            self.pause_btn.pack(side="left", padx=2)
        
        self.cancel_btn = ctk.CTkButton(
            btns, text="✕", width=32, height=28,
            font=ctk.CTkFont(size=14),
            fg_color=t["bg_input"],
            hover_color=t["neon_pink"],
            text_color=t["neon_pink"],
            corner_radius=6,
            command=self._do_cancel
        )
        self.cancel_btn.pack(side="left", padx=2)
        
        self.retry_btn = ctk.CTkButton(
            btns, text="↻", width=32, height=28,
            font=ctk.CTkFont(size=14),
            fg_color=t["neon_blue"],
            hover_color=t["blue_hover"],
            text_color="#ffffff",
            corner_radius=6,
            command=self._do_retry
        )
    
    def _load_thumb(self, url):
        if not HAS_PIL:
            return
        def fetch():
            try:
                with urllib.request.urlopen(url, timeout=10) as r:
                    data = r.read()
                img = Image.open(io.BytesIO(data)).resize((72, 40), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(72, 40))
                self.after(0, lambda: self.thumb.configure(image=ctk_img, text=""))
            except:
                pass
        threading.Thread(target=fetch, daemon=True).start()
    
    def _toggle_pause(self):
        if self._paused:
            if self.on_resume:
                self.on_resume()
        else:
            if self.on_pause:
                self.on_pause()
    
    def _do_cancel(self):
        if self.on_cancel:
            self.on_cancel()
    
    def _do_retry(self):
        if self.on_retry:
            self.on_retry()
    
    def set_waiting(self):
        """Set as waiting in queue."""
        t = DARK if self._mode == "dark" else LIGHT
        self._waiting = True
        self.stats.configure(text="⏳ Waiting...", text_color=t["text_dim"])
        self.progress.set(0)
        self.pause_btn.pack_forget()
    
    def set_paused(self, paused: bool):
        t = DARK if self._mode == "dark" else LIGHT
        self._paused = paused
        self.pause_btn.configure(text="▶" if paused else "⏸")
        if paused:
            self.stats.configure(text="⏸ Paused", text_color=t["neon_purple"])
            self.progress.configure(progress_color=t["neon_purple"])
        else:
            self.stats.configure(text="⚡ Resuming...", text_color=t["neon_cyan"])
            self.progress.configure(progress_color=t["neon_cyan"])
    
    def set_cancelled(self):
        t = DARK if self._mode == "dark" else LIGHT
        self._finished = True
        self.stats.configure(text="✕ Cancelled", text_color=t["text_muted"])
        self.progress.configure(progress_color=t["text_muted"])
        self.pause_btn.pack_forget()
        self.cancel_btn.pack_forget()
        self.retry_btn.pack(side="left", padx=2)
    
    def set_retrying(self):
        t = DARK if self._mode == "dark" else LIGHT
        self._finished = False
        self._waiting = False
        self.stats.configure(text="⚡ Starting...", text_color=t["neon_cyan"])
        self.progress.set(0)
        self.progress.configure(progress_color=t["neon_cyan"])
        self.retry_btn.pack_forget()
        self.pause_btn.pack(side="left", padx=2)
        self.cancel_btn.pack(side="left", padx=2)
    
    def update_progress(self, percent: float, speed: str = "", eta: str = ""):
        """Update progress bar and stats."""
        t = DARK if self._mode == "dark" else LIGHT
        
        self._waiting = False
        self.progress.set(percent / 100)
        
        # Show pause button if hidden
        if not self.pause_btn.winfo_ismapped():
            self.pause_btn.pack(side="left", padx=2)
        
        # Dynamic color based on progress
        if percent < 30:
            color = t["neon_cyan"]
        elif percent < 70:
            color = t["neon_blue"]
        else:
            color = t["neon_green"]
        
        self.progress.configure(progress_color=color)
        
        parts = [f"⚡ {percent:.1f}%"]
        if speed:
            parts.append(speed)
        if eta:
            parts.append(eta)
        
        self.stats.configure(text=" • ".join(parts), text_color=color)
    
    def set_complete(self, success: bool = True, message: str = ""):
        t = DARK if self._mode == "dark" else LIGHT
        self._finished = True
        self._waiting = False
        self.progress.set(1)
        self.pause_btn.pack_forget()
        self.cancel_btn.pack_forget()
        
        if success:
            self.stats.configure(text="✓ Complete!", text_color=t["neon_green"])
            self.progress.configure(progress_color=t["neon_green"])
        else:
            msg = message[:30] + "..." if len(message) > 30 else message
            self.stats.configure(text=f"✕ {msg}", text_color=t["neon_pink"])
            self.progress.configure(progress_color=t["neon_pink"])
            self.retry_btn.pack(side="left", padx=2)
    
    @property
    def is_finished(self):
        return self._finished
    
    @property
    def is_pending(self):
        return self._pending
    
    def start_download(self):
        """Start this download (change from pending to active)."""
        t = DARK if self._mode == "dark" else LIGHT
        self._pending = False
        self.stats.configure(text="⚡ Starting...", text_color=t["neon_cyan"])
        self.pause_btn.pack(side="left", padx=2)
    
    def update_theme(self, mode):
        self._mode = mode
        t = DARK if mode == "dark" else LIGHT
        
        self.configure(fg_color=t["bg_card"])
        self.title_lbl.configure(text_color=t["text"])
        self.pause_btn.configure(
            fg_color=t["bg_input"],
            hover_color=t["neon_purple"],
            text_color=t["neon_cyan"]
        )
        self.cancel_btn.configure(
            fg_color=t["bg_input"],
            hover_color=t["neon_pink"],
            text_color=t["neon_pink"]
        )
