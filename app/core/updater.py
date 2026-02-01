"""
Auto-updater for yt-dlp
Supports both development (pip) and frozen exe modes.
In frozen mode, downloads yt-dlp.exe standalone binary.
"""

import subprocess
import threading
import sys
import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)

# GitHub API URL for yt-dlp releases
YT_DLP_RELEASES_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
YT_DLP_EXE_NAME = "yt-dlp.exe"
APP_DATA_FOLDER = "YT-Downloader"


def is_frozen() -> bool:
    """Check if running as frozen exe (PyInstaller)."""
    return getattr(sys, 'frozen', False)


def get_app_data_dir() -> Path:
    """
    Get the app data directory for storing yt-dlp.exe and other files.
    Uses %LOCALAPPDATA%/YT-Downloader on Windows for frozen mode.
    This ensures yt-dlp.exe is always found regardless of where user moves the app.
    """
    if is_frozen():
        # Use LOCALAPPDATA for frozen mode (Windows standard)
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        if local_app_data:
            app_dir = Path(local_app_data) / APP_DATA_FOLDER
        else:
            # Fallback to user home
            app_dir = Path.home() / ".yt-downloader"
        
        # Create directory if not exists
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir
    else:
        # Development mode - use project directory
        return Path(__file__).parent.parent.parent


def get_ytdlp_exe_path() -> Path:
    """Get path to yt-dlp.exe (for frozen mode)."""
    return get_app_data_dir() / YT_DLP_EXE_NAME


def get_version_file_path() -> Path:
    """Get path to version tracking file."""
    return get_app_data_dir() / ".ytdlp_version"


class YtDlpUpdater:
    """Handles automatic updates for yt-dlp."""
    
    def __init__(self):
        self._update_callback: Optional[Callable[[str], None]] = None
        self._is_updating = False
    
    def set_callback(self, callback: Callable[[str], None]):
        """Set callback for update status messages."""
        self._update_callback = callback
    
    def _notify(self, message: str):
        """Send notification to callback."""
        logger.info(message)
        if self._update_callback:
            self._update_callback(message)
    
    def get_installed_version(self) -> Optional[str]:
        """Get currently installed yt-dlp version."""
        try:
            if is_frozen():
                # Check version file or run yt-dlp.exe --version
                exe_path = get_ytdlp_exe_path()
                if exe_path.exists():
                    result = subprocess.run(
                        [str(exe_path), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        return result.stdout.strip()
                return None
            else:
                # Development mode - use pip installed version
                result = subprocess.run(
                    [sys.executable, "-m", "yt_dlp", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    return result.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to get yt-dlp version: {e}")
        return None
    
    def _get_latest_release_info(self) -> Optional[dict]:
        """Fetch latest release info from GitHub API."""
        try:
            req = urllib.request.Request(
                YT_DLP_RELEASES_API,
                headers={"User-Agent": "yt-downloader-app"}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            logger.error(f"Failed to fetch release info: {e}")
            return None
    
    def check_update_available(self) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if an update is available without performing the update.
        Returns: (has_update, current_version, latest_version)
        """
        try:
            current_version = self.get_installed_version()
            
            release_info = self._get_latest_release_info()
            if not release_info:
                return False, current_version, None
            
            latest_version = release_info.get("tag_name", "").lstrip("v")
            
            if not current_version:
                return True, None, latest_version
            
            # Simple string comparison (yt-dlp uses YYYY.MM.DD format)
            has_update = latest_version > current_version
            return has_update, current_version, latest_version
            
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            return False, None, None
    
    def check_update_available_async(self, callback: Callable[[bool, Optional[str], Optional[str]], None]):
        """Check for updates in background and call callback with result."""
        def _run():
            result = self.check_update_available()
            callback(*result)
        
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
    
    def _download_file(self, url: str, dest: Path, on_progress: Optional[Callable[[int, int], None]] = None) -> bool:
        """Download a file from URL to destination."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "yt-downloader-app"})
            with urllib.request.urlopen(req, timeout=120) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192
                
                with open(dest, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if on_progress and total_size > 0:
                            on_progress(downloaded, total_size)
            return True
        except Exception as e:
            logger.error(f"Download failed: {e}")
            if dest.exists():
                dest.unlink()
            return False
    
    def _update_frozen(self) -> bool:
        """Update yt-dlp for frozen exe mode by downloading standalone binary."""
        self._notify("Checking for yt-dlp updates...")
        
        # Get latest release info
        release_info = self._get_latest_release_info()
        if not release_info:
            self._notify("Failed to check for updates")
            return False
        
        latest_version = release_info.get("tag_name", "").lstrip("v")
        current_version = self.get_installed_version()
        
        # Compare versions
        if current_version and current_version >= latest_version:
            self._notify(f"yt-dlp is up to date (v{current_version})")
            return False
        
        # Find Windows exe in assets
        exe_url = None
        for asset in release_info.get("assets", []):
            if asset.get("name") == "yt-dlp.exe":
                exe_url = asset.get("browser_download_url")
                break
        
        if not exe_url:
            self._notify("Could not find yt-dlp.exe in release")
            return False
        
        # Download new version
        self._notify(f"Downloading yt-dlp v{latest_version}...")
        exe_path = get_ytdlp_exe_path()
        temp_path = exe_path.with_suffix(".tmp")
        
        def on_progress(downloaded: int, total: int):
            percent = int(downloaded / total * 100)
            if percent % 20 == 0:  # Log every 20%
                self._notify(f"Downloading... {percent}%")
        
        if self._download_file(exe_url, temp_path, on_progress):
            # Replace old file with new one
            try:
                if exe_path.exists():
                    exe_path.unlink()
                temp_path.rename(exe_path)
                
                # Save version info
                version_file = get_version_file_path()
                version_file.write_text(latest_version)
                
                self._notify(f"yt-dlp updated to v{latest_version}")
                return True
            except Exception as e:
                logger.error(f"Failed to replace exe: {e}")
                self._notify(f"Update failed: {e}")
                if temp_path.exists():
                    temp_path.unlink()
                return False
        else:
            self._notify("Download failed")
            return False
    
    def _update_development(self) -> bool:
        """Update yt-dlp for development mode using pip."""
        self._notify("Updating yt-dlp...")
        
        try:
            # Use pip directly - more reliable when installed via pip
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                new_version = self.get_installed_version()
                self._notify(f"yt-dlp updated to v{new_version}")
                return True
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                self._notify(f"Update failed: {error_msg[:100]}")
                return False
                
        except subprocess.TimeoutExpired:
            self._notify("Update timed out")
            return False
        except Exception as e:
            self._notify(f"Update error: {str(e)}")
            return False

    def check_and_update(self) -> bool:
        """
        Check for yt-dlp updates and install if available.
        Returns True if update was performed.
        """
        if self._is_updating:
            return False
        
        self._is_updating = True
        try:
            if is_frozen():
                return self._update_frozen()
            else:
                return self._update_development()
        finally:
            self._is_updating = False
    
    def check_and_update_async(self, callback: Optional[Callable[[bool], None]] = None):
        """Check and update in background thread."""
        def _run():
            result = self.check_and_update()
            if callback:
                callback(result)
        
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
    
    def ensure_ytdlp_available(self) -> bool:
        """
        Ensure yt-dlp is available for use.
        In frozen mode, downloads if not present.
        Returns True if available.
        """
        if is_frozen():
            exe_path = get_ytdlp_exe_path()
            if not exe_path.exists():
                self._notify("yt-dlp not found, downloading...")
                return self._update_frozen()
            return True
        return True  # In dev mode, assume pip installed
    
    @property
    def is_updating(self) -> bool:
        return self._is_updating


# Global updater instance
_updater = YtDlpUpdater()


def check_for_updates(callback: Optional[Callable[[str], None]] = None):
    """
    Convenience function to check and update yt-dlp.
    Call this on app startup.
    """
    if callback:
        _updater.set_callback(callback)
    _updater.check_and_update_async()


def get_updater() -> YtDlpUpdater:
    """Get the global updater instance."""
    return _updater


def get_ytdlp_executable() -> str:
    """
    Get the path to yt-dlp executable.
    Returns 'yt-dlp' for dev mode, or full path to exe for frozen mode.
    """
    if is_frozen():
        return str(get_ytdlp_exe_path())
    return "yt-dlp"
