"""
Login Frame - Account section with OAuth URL display
"""

import customtkinter as ctk
from typing import Callable, Optional
from .theme import DARK, LIGHT, font, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG, PAD_SM, PAD_MD, PAD_LG, PAD_XL
from app.core.auth import AuthManager


class LoginFrame(ctk.CTkFrame):
    """Login/account section with OAuth modal."""
    
    def __init__(self, parent, on_login: Optional[Callable] = None, on_logout: Optional[Callable] = None):
        self._mode = "dark"
        t = DARK
        
        super().__init__(parent, fg_color=t["bg_card"], corner_radius=12)
        
        self.on_login = on_login
        self.on_logout = on_logout
        self._modal = None
        
        self.auth = AuthManager()
        
        self.grid_columnconfigure(1, weight=1)
        
        self.icon = ctk.CTkLabel(self, text="👤", font=ctk.CTkFont(size=20))
        self.icon.grid(row=0, column=0, padx=PAD_LG, pady=PAD_LG)
        
        self.status = ctk.CTkLabel(
            self, text="Not logged in",
            font=font(FONT_SIZE_SM),
            text_color=t["text_dim"], anchor="w"
        )
        self.status.grid(row=0, column=1, sticky="w")
        
        self.btn = ctk.CTkButton(
            self, text="➕ Login",
            width=100, height=34,
            font=font(FONT_SIZE_SM, bold=True),
            fg_color=t["blue"],
            hover_color=t["blue_hover"],
            text_color="#ffffff",
            corner_radius=8,
            command=self._show_login_modal
        )
        self.btn.grid(row=0, column=2, padx=PAD_LG, pady=PAD_LG)
        
        if self.auth.is_logged_in:
            self._set_logged_in(True, self.auth.email)
    
    def _show_login_modal(self):
        if self.auth.is_logged_in:
            self.auth.logout()
            self._set_logged_in(False)
            if self.on_logout:
                self.on_logout()
            return
        
        self._modal = LoginModal(
            self.winfo_toplevel(),
            mode=self._mode,
            auth=self.auth,
            on_complete=self._on_login_complete,
            on_cancel=self._on_modal_cancel
        )
    
    def _on_login_complete(self, email: str):
        self._modal = None
        self._set_logged_in(True, email)
        
        # Show success message
        from tkinter import messagebox
        messagebox.showinfo("Login Successful", "You have successfully logged in!")
        
        if self.on_login:
            self.on_login()
    
    def _on_modal_cancel(self):
        self._modal = None
    
    def _set_logged_in(self, logged: bool, email: str = ""):
        t = DARK if self._mode == "dark" else LIGHT
        
        if logged:
            self.icon.configure(text="✓")
            self.status.configure(text=email or "Logged in", text_color=t["neon_green"])
            self.btn.configure(
                text="Logout",
                fg_color=t["bg_input"],
                hover_color=t["bg_hover"],
                text_color=t["text"]
            )
        else:
            self.icon.configure(text="👤")
            self.status.configure(text="Not logged in", text_color=t["text_dim"])
            self.btn.configure(
                text="➕ Login",
                fg_color=t["blue"],
                hover_color=t["blue_hover"],
                text_color="#ffffff"
            )
    
    def set_logged_in(self, logged: bool, email: str = ""):
        self._set_logged_in(logged, email)
    
    def get_cookies_path(self) -> Optional[str]:
        return self.auth.cookies_path
    
    def update_theme(self, mode: str):
        self._mode = mode
        t = DARK if mode == "dark" else LIGHT
        
        self.configure(fg_color=t["bg_card"])
        self.icon.configure(text_color=t["text"])
        
        if self.auth.is_logged_in:
            self.status.configure(text_color=t["neon_green"])
            self.btn.configure(fg_color=t["bg_input"], hover_color=t["bg_hover"], text_color=t["text"])
        else:
            self.status.configure(text_color=t["text_dim"])
            self.btn.configure(fg_color=t["blue"], hover_color=t["blue_hover"], text_color="#ffffff")


class LoginModal(ctk.CTkToplevel):
    """OAuth login modal - BIGGER FONTS."""
    
    def __init__(self, parent, mode: str = "dark", auth: Optional[AuthManager] = None, 
                 on_complete=None, on_cancel=None):
        super().__init__(parent)
        
        self._mode = mode
        self.auth = auth or AuthManager()
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self._active_tab = "browser"
        t = DARK if mode == "dark" else LIGHT
        
        self.title("Login")
        self.geometry("450x520")
        self.resizable(False, False)
        self.configure(fg_color=t["bg_app"])
        
        self.transient(parent)
        self.grab_set()
        
        self.after(10, self._center)
        self._build_ui()
    
    def _center(self):
        self.update_idletasks()
        w, h = 450, 520
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
    
    def _build_ui(self):
        t = DARK if self._mode == "dark" else LIGHT
        
        # ========== HEADER ==========
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            header_frame, text="Login",
            font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
            text_color=t["text"]
        ).pack(side="left")
        
        # Tabs
        self.cookie_tab = ctk.CTkButton(
            header_frame, text="Cookie", width=80, height=32,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            fg_color="transparent",
            hover_color=t["bg_hover"],
            text_color=t["text_dim"],
            corner_radius=8,
            command=lambda: self._switch_tab("cookie")
        )
        self.cookie_tab.pack(side="right")
        
        self.oauth_tab = ctk.CTkButton(
            header_frame, text="Browser", width=80, height=32,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            fg_color=t["blue"],
            text_color="#ffffff",
            corner_radius=8,
            command=lambda: self._switch_tab("oauth")
        )
        self.oauth_tab.pack(side="right", padx=(0, 10))
        
        # ========== STATUS ==========
        self.status_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=t["text_dim"]
        )
        self.status_label.pack(pady=(0, 5))
        
        # ========== CONTENT ==========
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=20, pady=10)
        
        self._show_oauth_tab()
        
        # ========== CANCEL BUTTON ==========
        ctk.CTkButton(
            self, text="Cancel", height=44,
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            fg_color=t["bg_input"],
            hover_color=t["bg_hover"],
            text_color=t["text"],
            corner_radius=10,
            command=self._cancel
        ).pack(fill="x", padx=20, pady=(10, 20))
    
    def _switch_tab(self, tab: str):
        t = DARK if self._mode == "dark" else LIGHT
        self._active_tab = tab
        self.status_label.configure(text="")
        
        if tab == "oauth":
            self.oauth_tab.configure(fg_color=t["blue"], text_color="#ffffff")
            self.cookie_tab.configure(fg_color="transparent", text_color=t["text_dim"])
            self._show_oauth_tab()
        else:
            self.oauth_tab.configure(fg_color="transparent", text_color=t["text_dim"])
            self.cookie_tab.configure(fg_color=t["blue"], text_color="#ffffff")
            self._show_cookie_tab()
    
    def _show_oauth_tab(self):
        """Show Browser Login tab - opens browser for Google login."""
        t = DARK if self._mode == "dark" else LIGHT
        
        # Clear
        for w in self.content.winfo_children():
            w.destroy()
        
        # Detect browsers
        self._available_browsers = self.auth.detect_installed_browsers()
        
        # Info
        ctk.CTkLabel(
            self.content, text="Login with your Google account",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=t["text"]
        ).pack(pady=(20, 10))
        
        ctk.CTkLabel(
            self.content,
            text="A browser window will open for you to\nlogin to your Google account securely.",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=t["text_dim"],
            justify="center"
        ).pack(pady=10)
        
        # Browser selection if multiple browsers found
        if len(self._available_browsers) > 1:
            browser_frame = ctk.CTkFrame(self.content, fg_color="transparent")
            browser_frame.pack(fill="x", pady=15)
            
            ctk.CTkLabel(
                browser_frame, text="Select browser:",
                font=ctk.CTkFont(family="Inter", size=13),
                text_color=t["text_dim"]
            ).pack(side="left", padx=(20, 10))
            
            # Capitalize browser names for display
            display_names = [b.title() for b in self._available_browsers]
            self._browser_var = ctk.StringVar(value=self._available_browsers[0])
            
            self.browser_menu = ctk.CTkOptionMenu(
                browser_frame,
                values=display_names,
                variable=self._browser_var,
                width=120, height=36,
                font=ctk.CTkFont(family="Inter", size=13),
                fg_color=t["bg_input"],
                button_color=t["blue"],
                dropdown_fg_color=t["bg_card"],
                text_color=t["text"],
                command=self._on_browser_selected
            )
            self.browser_menu.pack(side="left")
        elif len(self._available_browsers) == 1:
            self._browser_var = ctk.StringVar(value=self._available_browsers[0])
            ctk.CTkLabel(
                self.content,
                text=f"Using {self._available_browsers[0].title()}",
                font=ctk.CTkFont(family="Inter", size=13),
                text_color=t["neon_cyan"]
            ).pack(pady=5)
        else:
            # No browsers found
            ctk.CTkLabel(
                self.content,
                text="⚠️ No supported browser found",
                font=ctk.CTkFont(family="Inter", size=14),
                text_color=t["red"]
            ).pack(pady=20)
            return
        
        # Login button
        self.login_btn = ctk.CTkButton(
            self.content, text="🔐  Login with Google", height=52,
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            fg_color=t["blue"],
            hover_color=t["blue_hover"],
            text_color="#ffffff",
            corner_radius=10,
            command=self._start_browser_login
        )
        self.login_btn.pack(fill="x", pady=(20, 20))
        
        # Note
        ctk.CTkLabel(
            self.content,
            text="💡 After login, the window will close automatically",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=t["text_muted"]
        ).pack()
    
    def _on_browser_selected(self, choice):
        """Handle browser selection from dropdown."""
        self._browser_var.set(choice.lower())
    
    def _show_cookie_tab(self):
        t = DARK if self._mode == "dark" else LIGHT
        
        for w in self.content.winfo_children():
            w.destroy()
        
        ctk.CTkLabel(
            self.content, text="Paste Netscape format cookies:",
            font=ctk.CTkFont(family="Inter", size=14),
            text_color=t["text_dim"], anchor="w"
        ).pack(fill="x", pady=(0, 10))
        
        self.cookie_text = ctk.CTkTextbox(
            self.content, height=150,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=t["bg_input"],
            text_color=t["text"],
            border_width=1,
            border_color=t["border"],
            corner_radius=10
        )
        self.cookie_text.pack(fill="x", pady=(0, 15))
        self.cookie_text.insert("0.0", "# Netscape HTTP Cookie File\n# Paste your cookies here...\n")
        
        self.import_btn = ctk.CTkButton(
            self.content, text="Import Cookies", height=48,
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            fg_color=t["neon_green"],
            hover_color=t["green_hover"],
            text_color="#000000",
            corner_radius=10,
            command=self._import_cookie
        )
        self.import_btn.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            self.content,
            text="💡 Use browser extension 'Get cookies.txt LOCALLY'",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=t["text_muted"]
        ).pack()
    
    def _start_browser_login(self):
        """Start browser login flow."""
        t = DARK if self._mode == "dark" else LIGHT
        browser = self._browser_var.get().lower()
        browser_name = browser.title()
        
        self.login_btn.configure(text="Opening browser...", state="disabled")
        self.status_label.configure(text=f"Starting {browser_name}...", text_color=t["blue"])
        
        def on_status(msg):
            self.after(0, lambda: self.status_label.configure(text=msg, text_color=t["neon_cyan"]))
        
        def on_complete(success, msg):
            self.after(0, lambda: self._handle_browser_login_result(success, msg))
        
        self.auth.login_with_browser(browser, on_status, on_complete)
    
    def _handle_browser_login_result(self, success: bool, msg: str):
        """Handle browser login result."""
        t = DARK if self._mode == "dark" else LIGHT
        self.login_btn.configure(text="�  Login with Google", state="normal")
        
        if success:
            self.status_label.configure(text="✓ " + msg, text_color=t["neon_green"])
            
            from tkinter import messagebox
            messagebox.showinfo("Login Successful", "You have successfully logged in!")
            
            if self.on_complete:
                self.on_complete(self.auth.email)
            self.after(500, self.destroy)
        else:
            self.status_label.configure(text="✕ " + msg, text_color=t["red"])
            from tkinter import messagebox
            messagebox.showerror("Login Failed", msg)
    
    def _import_cookie(self):
        t = DARK if self._mode == "dark" else LIGHT
        content = self.cookie_text.get("0.0", "end").strip()
        if not content or "Paste your cookies here" in content:
            self.status_label.configure(text="Please paste cookies first", text_color=t["red"])
            return
        success, msg = self.auth.import_cookies(content)
        if success:
            self.status_label.configure(text="✓ " + msg, text_color=t["neon_green"])
            if self.on_complete:
                self.on_complete(self.auth.email)
            self.after(1000, self.destroy)
        else:
            self.status_label.configure(text="✕ " + msg, text_color=t["red"])
    
    def _cancel(self):
        if self.on_cancel:
            self.on_cancel()
        self.destroy()
