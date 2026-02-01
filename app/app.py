"""
Main Application
"""

import customtkinter as ctk
from app.ui.main_window import MainWindow
from app.ui.theme import DARK, LIGHT, init_fonts
from app.core.updater import get_updater


class App(ctk.CTk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Init fonts after Tk ready
        init_fonts()
        
        self._mode = "dark"
        
        # Window setup
        self.title("YouTube Video Downloader")
        self.geometry("1000x680")
        self.minsize(900, 600)
        
        # Apply theme
        self._apply_theme()
        self._center()
        
        # Main content
        self.main = MainWindow(self, on_theme_toggle=self.toggle_theme)
        self.main.pack(fill="both", expand=True)
        
        # Check for yt-dlp updates in background (after UI is ready)
        self._check_for_updates()
    
    def _check_for_updates(self):
        """Check for yt-dlp updates and notify UI if available."""
        updater = get_updater()
        
        def on_check_complete(has_update: bool, current: str, latest: str):
            if has_update and latest:
                print(f"[Updater] New version available: v{latest} (current: v{current})")
                # Update UI on main thread
                self.after(0, lambda: self.main.show_update_available(latest))
            else:
                print(f"[Updater] yt-dlp is up to date (v{current})")
        
        updater.check_update_available_async(on_check_complete)
    
    def _center(self):
        """Center window on screen."""
        w, h = 1000, 680
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
    
    def _apply_theme(self):
        """Apply current theme."""
        ctk.set_appearance_mode(self._mode)
        t = DARK if self._mode == "dark" else LIGHT
        self.configure(fg_color=t["bg_app"])
    
    def toggle_theme(self):
        """Toggle dark/light mode."""
        self._mode = "light" if self._mode == "dark" else "dark"
        self._apply_theme()
        if hasattr(self, 'main'):
            self.main.update_theme(self._mode)
