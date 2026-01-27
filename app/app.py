"""
Main Application
"""

import customtkinter as ctk
from app.ui.main_window import MainWindow
from app.ui.theme import DARK, LIGHT, init_fonts


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
