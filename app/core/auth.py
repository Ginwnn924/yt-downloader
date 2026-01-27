"""
Authentication Manager - Cookie handling for yt-dlp
"""

import os
import json
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable


class AuthManager:
    """Manages authentication for YouTube downloads."""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".yt-downloader"
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.cookies_file = self.config_dir / "cookies.txt"
        self.auth_file = self.config_dir / "auth.json"
        
        self._logged_in = False
        self._email = ""
        
        self._load_auth_state()
    
    def _load_auth_state(self):
        """Load saved auth state."""
        if self.auth_file.exists():
            try:
                with open(self.auth_file, "r") as f:
                    data = json.load(f)
                    self._logged_in = data.get("logged_in", False)
                    self._email = data.get("email", "")
            except:
                pass
        
        # Check if cookies exist
        if self.cookies_file.exists():
            self._logged_in = True
    
    def _save_auth_state(self):
        """Save auth state."""
        try:
            with open(self.auth_file, "w") as f:
                json.dump({
                    "logged_in": self._logged_in,
                    "email": self._email
                }, f)
        except:
            pass
    
    @property
    def is_logged_in(self) -> bool:
        return self._logged_in and self.cookies_file.exists()
    
    @property
    def email(self) -> str:
        return self._email
    
    def get_yt_dlp_auth_args(self) -> list:
        """Get yt-dlp arguments for authentication."""
        args = []
        if self.cookies_file.exists():
            args.extend(["--cookies", str(self.cookies_file)])
        return args
    
    @property
    def cookies_path(self) -> Optional[str]:
        """Get cookies file path for yt-dlp."""
        if self.cookies_file.exists():
            return str(self.cookies_file)
        return None
    
    def detect_installed_browsers(self) -> list:
        """Detect installed browsers on the system."""
        browsers = []
        
        import platform
        system = platform.system()
        
        if system == "Windows":
            import winreg
            
            browser_paths = {
                "chrome": [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                ],
                "firefox": [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe",
                ],
                "edge": [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
                ],
                "brave": [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\brave.exe",
                ],
            }
            
            for browser, paths in browser_paths.items():
                for path in paths:
                    try:
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                        winreg.CloseKey(key)
                        if browser not in browsers:
                            browsers.append(browser)
                        break
                    except:
                        pass
            
            # Also check common paths
            common_paths = {
                "chrome": [
                    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
                ],
                "firefox": [
                    os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
                    os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
                ],
                "edge": [
                    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
                ],
            }
            
            for browser, paths in common_paths.items():
                if browser not in browsers:
                    for p in paths:
                        if os.path.exists(p):
                            browsers.append(browser)
                            break
        
        elif system == "Darwin":  # macOS
            mac_browsers = {
                "chrome": "/Applications/Google Chrome.app",
                "firefox": "/Applications/Firefox.app",
                "edge": "/Applications/Microsoft Edge.app",
                "safari": "/Applications/Safari.app",
            }
            for browser, path in mac_browsers.items():
                if os.path.exists(path):
                    browsers.append(browser)
        
        else:  # Linux
            import shutil
            linux_browsers = {
                "chrome": ["google-chrome", "google-chrome-stable"],
                "firefox": ["firefox"],
                "edge": ["microsoft-edge"],
            }
            for browser, cmds in linux_browsers.items():
                for cmd in cmds:
                    if shutil.which(cmd):
                        browsers.append(browser)
                        break
        
        return browsers
    
    def import_cookies(self, cookie_content: str) -> tuple[bool, str]:
        """Import cookies from Netscape format string."""
        lines = cookie_content.strip().split("\n")
        valid_lines = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                valid_lines.append(line)
                continue
            
            parts = line.split("\t")
            if len(parts) >= 7:
                valid_lines.append(line)
        
        cookie_count = sum(1 for l in valid_lines if l and not l.startswith("#"))
        
        if cookie_count == 0:
            return False, "No valid cookies found"
        
        try:
            content = "# Netscape HTTP Cookie File\n"
            content += "# https://curl.haxx.se/docs/http-cookies.html\n"
            content += "\n".join(valid_lines)
            
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            self._logged_in = True
            self._email = "Logged in (Cookies)"
            self._save_auth_state()
            
            return True, f"Successfully imported {cookie_count} cookies"
        except Exception as e:
            return False, str(e)
    
    def extract_cookies_from_browser(self, browser: str = "chrome") -> tuple:
        """
        Extract YouTube cookies from installed browser.
        Uses yt-dlp's --cookies-from-browser feature.
        """
        try:
            cmd = [
                "yt-dlp",
                "--cookies-from-browser", browser,
                "--cookies", str(self.cookies_file),
                "--skip-download",
                "--no-warnings",
                "https://www.youtube.com"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if self.cookies_file.exists():
                content = self.cookies_file.read_text()
                if ".youtube.com" in content or ".google.com" in content:
                    self._logged_in = True
                    self._email = f"Logged in ({browser.title()})"
                    self._save_auth_state()
                    return True, f"Cookies extracted from {browser.title()}"
                else:
                    return False, f"No YouTube cookies found in {browser.title()}"
            else:
                return False, result.stderr[:100] if result.stderr else "Failed to extract"
                
        except subprocess.TimeoutExpired:
            return False, "Extraction timed out"
        except Exception as e:
            return False, str(e)[:100]
    
    def login_with_browser(self, browser: str = "edge", on_status=None, on_complete=None):
        """
        Open browser with Selenium for Google login and capture cookies.
        """
        def run_login():
            driver = None
            try:
                browser_name = browser.title()
                if on_status:
                    on_status(f"Opening {browser_name}...")
                
                from selenium import webdriver
                
                if browser == "edge":
                    from selenium.webdriver.edge.options import Options
                    
                    options = Options()
                    options.add_argument("--start-maximized")
                    options.add_argument("--disable-blink-features=AutomationControlled")
                    options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    
                    if on_status:
                        on_status(f"Starting {browser_name}...")
                    
                    # Try without explicit driver path first (uses system PATH)
                    try:
                        driver = webdriver.Edge(options=options)
                    except:
                        # Fallback to webdriver-manager
                        from selenium.webdriver.edge.service import Service
                        from webdriver_manager.microsoft import EdgeChromiumDriverManager
                        service = Service(EdgeChromiumDriverManager().install())
                        driver = webdriver.Edge(service=service, options=options)
                        
                elif browser == "chrome":
                    from selenium.webdriver.chrome.options import Options
                    
                    options = Options()
                    options.add_argument("--start-maximized")
                    options.add_argument("--disable-blink-features=AutomationControlled")
                    options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    
                    if on_status:
                        on_status(f"Starting {browser_name}...")
                    
                    try:
                        driver = webdriver.Chrome(options=options)
                    except:
                        from selenium.webdriver.chrome.service import Service
                        from webdriver_manager.chrome import ChromeDriverManager
                        service = Service(ChromeDriverManager().install())
                        driver = webdriver.Chrome(service=service, options=options)
                        
                elif browser == "firefox":
                    from selenium.webdriver.firefox.options import Options
                    
                    options = Options()
                    
                    if on_status:
                        on_status(f"Starting {browser_name}...")
                    
                    try:
                        driver = webdriver.Firefox(options=options)
                    except:
                        from selenium.webdriver.firefox.service import Service
                        from webdriver_manager.firefox import GeckoDriverManager
                        service = Service(GeckoDriverManager().install())
                        driver = webdriver.Firefox(service=service, options=options)
                else:
                    if on_complete:
                        on_complete(False, f"Unsupported browser: {browser}")
                    return
                
                # Open Google login
                driver.get("https://accounts.google.com/ServiceLogin?continue=https://www.youtube.com")
                
                if on_status:
                    on_status("Please login in the browser window...")
                
                # Wait for login (check URL)
                import time
                max_wait = 300  # 5 minutes
                start = time.time()
                
                while time.time() - start < max_wait:
                    try:
                        current_url = driver.current_url
                        if "youtube.com" in current_url and "accounts.google" not in current_url:
                            # Get cookies
                            cookies = driver.get_cookies()
                            
                            # Convert to Netscape format
                            lines = ["# Netscape HTTP Cookie File"]
                            for c in cookies:
                                domain = c.get("domain", "")
                                if ".youtube.com" in domain or ".google.com" in domain:
                                    flag = "TRUE" if domain.startswith(".") else "FALSE"
                                    path = c.get("path", "/")
                                    secure = "TRUE" if c.get("secure", False) else "FALSE"
                                    expiry = str(int(c.get("expiry", 0)))
                                    name = c.get("name", "")
                                    value = c.get("value", "")
                                    lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")
                            
                            driver.quit()
                            driver = None
                            
                            if len(lines) > 1:
                                with open(self.cookies_file, "w") as f:
                                    f.write("\n".join(lines))
                                
                                self._logged_in = True
                                self._email = f"Logged in ({browser_name})"
                                self._save_auth_state()
                                
                                if on_complete:
                                    on_complete(True, "Login successful!")
                                return
                            else:
                                if on_complete:
                                    on_complete(False, "No cookies captured")
                                return
                    except:
                        pass
                    time.sleep(1)
                
                if driver:
                    driver.quit()
                if on_complete:
                    on_complete(False, "Login timed out")
                    
            except Exception as e:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                if on_complete:
                    on_complete(False, str(e)[:100])
        
        threading.Thread(target=run_login, daemon=True).start()
    
    def logout(self):
        """Clear saved authentication."""
        try:
            if self.cookies_file.exists():
                self.cookies_file.unlink()
            if self.auth_file.exists():
                self.auth_file.unlink()
        except:
            pass
        
        self._logged_in = False
        self._email = ""
