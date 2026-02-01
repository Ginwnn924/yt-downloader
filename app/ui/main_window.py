"""
Main Window - 2-column layout with proper playlist progress tracking
"""

import customtkinter as ctk
import threading
from tkinter import messagebox
from typing import Callable, Optional

from .login_frame import LoginFrame
from .download_frame import DownloadFrame
from .progress_frame import ProgressFrame
from .theme import DARK, LIGHT, font, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG, PAD_SM, PAD_MD, PAD_LG, PAD_XL
from app.core.downloader import Downloader
from app.core.updater import get_updater


class MainWindow(ctk.CTkFrame):
    """Main window with 2-column layout."""
    
    def __init__(self, parent, on_theme_toggle: Optional[Callable] = None):
        self._mode = "dark"
        t = DARK
        
        super().__init__(parent, fg_color=t["bg_app"], corner_radius=0)
        
        self._parent = parent
        self._on_theme_toggle = on_theme_toggle
        
        # Download tracking
        self._pending_videos = []  # Videos loaded but not yet downloading
        self._active_downloaders = {}
        self._download_semaphore = threading.Semaphore(3)  # Limit concurrent downloads
        self._task_context = {}
        self._paused_ids = set()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._build_header()
        self._build_content()
    
    def _build_header(self):
        """Header bar."""
        t = DARK if self._mode == "dark" else LIGHT
        
        hdr = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=0, height=60)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)
        self.header = hdr
        
        self.title_lbl = ctk.CTkLabel(
            hdr,
            text="YouTube Video Downloader",
            font=font(FONT_SIZE_LG, bold=True),
            text_color=t["text"]
        )
        self.title_lbl.grid(row=0, column=0, padx=PAD_XL, pady=PAD_MD, sticky="w")
        
        # Update button (hidden by default, shown when update available)
        self._update_available = False
        self._latest_version = None
        
        self.update_btn = ctk.CTkButton(
            hdr,
            text="🔄 Update",
            width=100,
            height=36,
            font=font(FONT_SIZE_SM, bold=True),
            fg_color="#22c55e",  # Green
            hover_color="#16a34a",
            text_color="white",
            corner_radius=8,
            command=self._do_update
        )
        # Don't grid yet - will be shown when update is available
        
        self.theme_btn = ctk.CTkButton(
            hdr,
            text="☀️" if self._mode == "dark" else "🌙",
            width=42,
            height=36,
            font=ctk.CTkFont(size=16),
            fg_color=t["bg_input"],
            hover_color=t["bg_hover"],
            text_color=t["text"],
            corner_radius=8,
            command=self._toggle_theme
        )
        self.theme_btn.grid(row=0, column=3, padx=PAD_XL, pady=PAD_MD)
    
    def _build_content(self):
        """2-column content."""
        t = DARK if self._mode == "dark" else LIGHT
        
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=PAD_XL, pady=PAD_XL)
        content.grid_columnconfigure(0, weight=1, uniform="col")
        content.grid_columnconfigure(1, weight=1, uniform="col")
        content.grid_rowconfigure(0, weight=1)
        self.content = content
        
        # Left column
        left = ctk.CTkFrame(content, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)
        
        self.login_frame = LoginFrame(left, on_login=self._login, on_logout=self._logout)
        self.login_frame.grid(row=0, column=0, sticky="ew", pady=(0, PAD_MD))
        
        self.download_frame = DownloadFrame(left, on_download=self._download, on_load_url=self._load_url)
        self.download_frame.grid(row=1, column=0, sticky="nsew")
        
        # Right column
        self.progress_frame = ProgressFrame(
            content,
            on_pause=self._pause_download,
            on_resume=self._resume_download,
            on_cancel=self._cancel_download,
            on_retry=lambda id: None
        )
        self.progress_frame.grid(row=0, column=1, sticky="nsew", padx=(PAD_SM, 0))
    
    def _toggle_theme(self):
        if self._on_theme_toggle:
            self._on_theme_toggle()
    
    def update_theme(self, mode: str):
        self._mode = mode
        t = DARK if mode == "dark" else LIGHT
        
        self.configure(fg_color=t["bg_app"])
        self.header.configure(fg_color=t["bg_card"])
        self.title_lbl.configure(text_color=t["text"])
        self.theme_btn.configure(
            text="☀️" if mode == "dark" else "🌙",
            fg_color=t["bg_input"],
            hover_color=t["bg_hover"],
            text_color=t["text"]
        )
        
        self.login_frame.update_theme(mode)
        self.download_frame.update_theme(mode)
        self.progress_frame.update_theme(mode)
    
    # === Update Methods ===
    
    def show_update_available(self, latest_version: str):
        """Show the update button when a new version is available."""
        self._update_available = True
        self._latest_version = latest_version
        self.update_btn.configure(text=f"🔄 v{latest_version}")
        self.update_btn.grid(row=0, column=2, padx=(0, PAD_SM), pady=PAD_MD)
    
    def hide_update_button(self):
        """Hide the update button."""
        self._update_available = False
        self.update_btn.grid_forget()
    
    def _do_update(self):
        """Handle update button click."""
        self.update_btn.configure(text="Updating...", state="disabled")
        
        def on_update_done(success: bool):
            self._parent.after(0, lambda: self._on_update_complete(success))
        
        updater = get_updater()
        updater.check_and_update_async(callback=on_update_done)
    
    def _on_update_complete(self, success: bool):
        """Handle update completion."""
        if success:
            self.hide_update_button()
            new_version = get_updater().get_installed_version()
            result = messagebox.askyesno(
                "Update Successful",
                f"yt-dlp has been updated to v{new_version}!\n\n"
                "Please restart the app for changes to take effect.\n\n"
                "Restart now?",
                icon="info"
            )
            if result:
                self._restart_app()
        else:
            self.update_btn.configure(text="🔄 Retry", state="normal")
            messagebox.showerror(
                "Update Failed",
                "Failed to update yt-dlp.\n\nPlease check your internet connection and try again."
            )
    
    def _restart_app(self):
        """Restart the application."""
        import sys
        import os
        
        # Get the executable or script path
        if getattr(sys, 'frozen', False):
            # Running as exe
            os.execl(sys.executable, sys.executable)
        else:
            # Running as script
            os.execl(sys.executable, sys.executable, *sys.argv)

    # === Handlers ===
    
    def _login(self):
        # Login handled by LoginFrame callback, nothing needed here
        pass
    
    def _logout(self):
        self.login_frame.set_logged_in(False)
    
    def _load_url(self, url: str):
        """Load video info and add to progress as pending."""
        def task():
            try:
                cookies = self.login_frame.get_cookies_path()
                dl = Downloader(cookies_file=cookies)
                info, error = dl.get_video_info(url)
                if error:
                    err_msg = error  # Capture value
                    self._parent.after(0, lambda e=err_msg: self.download_frame.on_load_error(e))
                elif info:
                    self._parent.after(0, lambda i=info: self._on_video_loaded(url, i))
                else:
                    self._parent.after(0, lambda: self.download_frame.on_load_error("Failed to load video"))
            except Exception as e:
                err_str = str(e)
                self._parent.after(0, lambda es=err_str: self.download_frame.on_load_error(es))
        threading.Thread(target=task, daemon=True).start()
    
    def _on_video_loaded(self, url: str, info: dict):
        """Add loaded video(s) to progress as pending."""
        if not info:
            self.download_frame.on_load_error("Failed to load")
            return
        
        is_playlist = info.get("is_playlist", False)
        added_count = 0
        
        if is_playlist:
            entries = list(info.get("entries", []))
            for i, entry in enumerate(entries):
                video_id = entry.get("id", str(i))
                video_url = entry.get("url") or entry.get("webpage_url") or f"https://youtube.com/watch?v={video_id}"
                title = entry.get("title", f"Video {i+1}")
                thumb = entry.get("thumbnail", "")
                
                download_id = f"pending_{len(self._pending_videos)}_{video_id}"
                self._pending_videos.append({
                    "id": download_id,
                    "url": video_url,
                    "title": title,
                    "thumbnail": thumb
                })
                
                self.progress_frame.add_download(
                    download_id=download_id,
                    title=title,
                    url=video_url,
                    thumbnail_url=thumb,
                    pending=True
                )
                added_count += 1
        else:
            title = info.get("title", "Unknown")
            thumb = info.get("thumbnail", "")
            if not thumb:
                thumbs = info.get("thumbnails", [])
                if thumbs:
                    thumb = thumbs[-1].get("url", "")
            
            download_id = f"pending_{len(self._pending_videos)}_{url[-11:]}"
            self._pending_videos.append({
                "id": download_id,
                "url": url,
                "title": title,
                "thumbnail": thumb
            })
            
            self.progress_frame.add_download(
                download_id=download_id,
                title=title,
                url=url,
                thumbnail_url=thumb,
                pending=True
            )
            added_count = 1
        
        self.download_frame.on_video_loaded(added_count)
    
    def _download(self):
        """Start downloading all pending items."""
        pending_ids = self.progress_frame.get_pending_ids()
        if not pending_ids:
            return
        
        # Get quality and output dir
        quality_height = self.download_frame.get_quality_height()
        output_dir = self.download_frame.get_output_dir()
        cookies = self.login_frame.get_cookies_path()
        
        format_str = f"bv*[height<={quality_height}]+ba/b[height<={quality_height}]" if quality_height else "bv*+ba/b"
        
        # Identify videos to start
        videos_to_start = [v for v in self._pending_videos if v["id"] in pending_ids]
        self._pending_videos = [v for v in self._pending_videos if v["id"] not in pending_ids]
        
        # Update pending count
        self.download_frame.set_pending_count(len(self._pending_videos))
        
        # Start all tasks
        for video in videos_to_start:
            self._start_download_task(video, format_str, output_dir, cookies)
            
    def _start_download_task(self, video, format_str, output_dir, cookies):
        """Start a single download task in a separate thread."""
        download_id = video["id"]
        
        # Store context for resume
        self._task_context[download_id] = {
            "video": video,
            "format_str": format_str,
            "output_dir": output_dir,
            "cookies": cookies
        }
        
        # Create a dedicated downloader for this task
        dl = Downloader(output_dir=output_dir, cookies_file=cookies)
        self._active_downloaders[download_id] = dl
        
        self.progress_frame.start_download(download_id)
        
        dl.set_callbacks(
            on_progress=lambda i: self._parent.after(0, lambda: self._on_progress(download_id, i)),
            on_complete=lambda f: self._parent.after(0, lambda: self._on_task_done(download_id, True, f)),
            on_error=lambda e: self._parent.after(0, lambda: self._on_task_done(download_id, False, e))
        )
        
        def task():
            # Wait for slot
            with self._download_semaphore:
                # Check directly if it was cancelled while waiting
                if download_id in self._active_downloaders:
                    dl.download_video(video["url"], format_str)
        
        threading.Thread(target=task, daemon=True).start()
    
    def _on_progress(self, download_id: str, info: dict):
        """Update progress for specific download."""
        self.progress_frame.update_download(
            download_id,
            info.get("percent", 0),
            info.get("speed", ""),
            info.get("eta", "")
        )
    
    def _on_task_done(self, download_id: str, success: bool, msg: str):
        """Handle task completion."""
        if download_id in self._paused_ids:
            if download_id in self._active_downloaders:
                del self._active_downloaders[download_id]
            return

        self.progress_frame.complete_download(download_id, success, msg if not success else "")
        
        # Check for 403 error - show message once and cancel all
        if not success and ("403" in msg or "Forbidden" in msg):
            self._handle_403_error()
        
        if download_id in self._task_context:
            del self._task_context[download_id]
            
        if download_id in self._active_downloaders:
            del self._active_downloaders[download_id]
    
    def _handle_403_error(self):
        """Handle 403 error by showing message and cancelling all downloads."""
        # Only show once - use a flag
        if hasattr(self, '_403_shown') and self._403_shown:
            return
        self._403_shown = True
        
        # Cancel all remaining downloads first
        for did in list(self._active_downloaders.keys()):
            if did in self._active_downloaders:
                self._active_downloaders[did].cancel()
        
        # Show message box
        result = messagebox.askyesno(
            "Update Required",
            "HTTP 403 Forbidden error detected.\n\n"
            "This usually means yt-dlp needs to be updated.\n\n"
            "Would you like to update yt-dlp now?",
            icon="warning"
        )
        
        if result:
            self._do_update()
        
        # Reset flag after a delay (allow new errors to show again later)
        self._parent.after(5000, lambda: setattr(self, '_403_shown', False))
    
    def _cancel_download(self, download_id: str):
        """Cancel specific download."""
        if download_id in self._paused_ids:
            self._paused_ids.remove(download_id)
        if download_id in self._task_context:
            del self._task_context[download_id]
            
        if download_id in self._active_downloaders:
            self._active_downloaders[download_id].cancel()
            del self._active_downloaders[download_id]
        self.download_frame.set_downloading(False)

    def _pause_download(self, download_id: str):
        """Pause a download."""
        if download_id in self._active_downloaders:
            self._paused_ids.add(download_id)
            self._active_downloaders[download_id].cancel()

    def _resume_download(self, download_id: str):
        """Resume a download."""
        if download_id in self._paused_ids:
            self._paused_ids.remove(download_id)
        
        if download_id in self._task_context:
            ctx = self._task_context[download_id]
            self._start_download_task(
                ctx["video"],
                ctx["format_str"],
                ctx["output_dir"],
                ctx["cookies"]
            )

