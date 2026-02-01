"""
Downloader - yt-dlp wrapper with playlist support and anti-blocking
Supports both Python module and external yt-dlp.exe (for frozen apps)
"""

from typing import Callable, Optional, Any
from pathlib import Path
import threading
import subprocess
import json
import re

try:
    from yt_dlp import YoutubeDL
except ImportError:
    YoutubeDL = None

from .updater import is_frozen, get_ytdlp_exe_path


import sys

def _should_use_subprocess() -> bool:
    """
    Always use subprocess for yt-dlp interactions.
    This ensures we always use the latest version after an update,
    without needing to reload modules or restart the app.
    """
    return True


class Downloader:
    """Wrapper around yt-dlp for downloading videos and playlists."""
    
    # Common user agent to avoid blocks
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def __init__(
        self,
        output_dir: str = "downloads",
        quality: str = "best",
        cookies_file: Optional[str] = None
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.quality = quality
        self.cookies_file = cookies_file
        
        self._progress_callback: Optional[Callable] = None
        self._complete_callback: Optional[Callable] = None
        self._error_callback: Optional[Callable] = None
        self._video_start_callback: Optional[Callable] = None
        self._is_downloading: bool = False
        self._cancel_requested: bool = False
        self._current_process: Optional[subprocess.Popen] = None
        
        # Always use subprocess
        self._use_subprocess = _should_use_subprocess()
    
    def set_callbacks(
        self,
        on_progress: Optional[Callable[[dict], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_video_start: Optional[Callable[[dict], None]] = None
    ):
        """Set callback functions."""
        self._progress_callback = on_progress
        self._complete_callback = on_complete
        self._error_callback = on_error
        self._video_start_callback = on_video_start
    
    def _get_format_string(self, height: int = 0) -> str:
        """Get yt-dlp format string for given height."""
        if height > 0:
            return f"bv*[height<={height}]+ba/b[height<={height}]"
        return "bv*+ba/b"  # Best available
    
    def _get_base_options(self) -> dict:
        """Get base options to avoid 403 errors."""
        return {
            # Anti-blocking options
            "http_headers": {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-us,en;q=0.5",
                "Sec-Fetch-Mode": "navigate",
            },
            # Retry and timeout
            "retries": 3,
            "fragment_retries": 10,
            "socket_timeout": 30,
            "extractor_retries": 3,
            # Output control
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,  # Raise exception on error so we can catch it
        }
    
    def _get_options(self, format_str: str = "bv*+ba/b") -> dict:
        """Build yt-dlp options."""
        opts = self._get_base_options()
        opts.update({
            "outtmpl": str(self.output_dir / "%(title)s.%(ext)s"),
            "format": format_str,
            "merge_output_format": "mp4",
            "noplaylist": False,
            "progress_hooks": [self._progress_hook],
            "postprocessor_hooks": [self._postprocessor_hook],
            "ffmpeg_location": "ffmpeg" if not is_frozen() else None # Optional hint
        })
        
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file
        
        return opts
    
    def _progress_hook(self, d: dict):
        """Handle progress updates."""
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed", 0)
            eta = d.get("eta", 0)
            
            percent = (downloaded / total * 100) if total > 0 else 0
            
            progress_info = {
                "status": "downloading",
                "percent": percent,
                "downloaded": self._format_bytes(downloaded),
                "total": self._format_bytes(total),
                "speed": self._format_bytes(speed) + "/s" if speed else "",
                "eta": self._format_time(eta) if eta else "",
            }
            
            if self._progress_callback:
                self._progress_callback(progress_info)
        
            if self._cancel_requested:
                raise ValueError("cancelled")
        
        elif d.get("status") == "finished":
            if self._progress_callback:
                self._progress_callback({"status": "processing", "percent": 100})
    
    def _postprocessor_hook(self, d: dict):
        """Handle post-processing."""
        if d.get("status") == "finished":
            filepath = d.get("info_dict", {}).get("filepath", "")
            if self._complete_callback:
                self._complete_callback(filepath)
    
    @staticmethod
    def _format_bytes(bytes_value: float) -> str:
        if not bytes_value:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB"]:
            if abs(bytes_value) < 1024:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024
        return f"{bytes_value:.1f} TB"
    
    @staticmethod
    def _format_time(seconds: int) -> str:
        if not seconds:
            return ""
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
    
    # === Subprocess mode methods (for external yt-dlp.exe) ===
    
    def _build_cmd_args(self, url: str, format_str: str, extract_only: bool = False) -> list:
        """Build command line arguments for yt-dlp."""
        
        # Determine executable
        if is_frozen():
            exe = str(get_ytdlp_exe_path())
            args = [exe]
        else:
            # Run via python module
            args = [sys.executable, "-m", "yt_dlp"]
        
        if extract_only:
            args.extend(["-j", "--flat-playlist"])
        else:
            args.extend([
                "-f", format_str,
                "-o", str(self.output_dir / "%(title)s.%(ext)s"),
                "--merge-output-format", "mp4",
                "--newline",  # Progress on new lines
                "--progress-template", "download:%(progress._percent_str)s %(progress._speed_str)s ETA:%(progress._eta_str)s",
            ])
        
        # Common anti-blocking args
        args.extend([
            "--user-agent", self.USER_AGENT,
            "--retries", "10",
            "--socket-timeout", "30",
        ])
        
        if self.cookies_file:
            args.extend(["--cookies", self.cookies_file])
        
        args.append(url)
        return args
    
    def _parse_progress_line(self, line: str) -> Optional[dict]:
        """Parse progress output from yt-dlp."""
        # Format: "download:  45.2% 5.23MiB/s ETA:00:32"
        if line.startswith("download:"):
            try:
                parts = line[9:].strip().split()
                percent_str = parts[0].replace("%", "").strip()
                percent = float(percent_str) if percent_str != "N/A" else 0
                speed = parts[1] if len(parts) > 1 else ""
                eta = parts[2].replace("ETA:", "") if len(parts) > 2 else ""
                
                return {
                    "status": "downloading",
                    "percent": percent,
                    "speed": speed if speed != "N/A" else "",
                    "eta": eta if eta != "N/A" else "",
                }
            except:
                pass
        return None
    
    def _download_video_subprocess(self, url: str, format_str: str) -> bool:
        """Download video using subprocess (for frozen mode)."""
        if self._cancel_requested:
            return False
        
        try:
            args = self._build_cmd_args(url, format_str)
            
            # Start process
            self._current_process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Read output line by line
            for line in self._current_process.stdout:
                if self._cancel_requested:
                    self._current_process.terminate()
                    return False
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse progress
                progress = self._parse_progress_line(line)
                if progress and self._progress_callback:
                    self._progress_callback(progress)
                
                # Check for completion
                if "[Merger]" in line or "has already been downloaded" in line:
                    if self._progress_callback:
                        self._progress_callback({"status": "processing", "percent": 100})
            
            # Wait for completion
            return_code = self._current_process.wait()
            self._current_process = None
            
            if return_code == 0:
                if self._complete_callback:
                    self._complete_callback("")
                return True
            else:
                if self._error_callback:
                    self._error_callback(f"Download failed with code {return_code}")
                return False
                
        except Exception as e:
            if self._error_callback:
                self._error_callback(str(e))
            return False
        finally:
            self._current_process = None
    
    def _get_video_info_subprocess(self, url: str) -> tuple:
        """Get video info using subprocess (for frozen mode)."""
        try:
            args = self._build_cmd_args(url, "", extract_only=True)
            
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                return None, result.stderr or "Failed to get video info"
            
            # Parse JSON output (each line is a JSON object)
            lines = result.stdout.strip().split("\n")
            entries = []
            
            for line in lines:
                if line.strip():
                    try:
                        info = json.loads(line)
                        entries.append(info)
                    except json.JSONDecodeError:
                        continue
            
            if not entries:
                return None, "No video info found"
            
            if len(entries) == 1:
                # Single video
                info = entries[0]
                info["is_playlist"] = False
                return info, None
            else:
                # Playlist
                return {
                    "is_playlist": True,
                    "title": "Playlist",
                    "playlist_count": len(entries),
                    "entries": entries,
                }, None
                
        except subprocess.TimeoutExpired:
            return None, "Timeout while getting video info"
        except Exception as e:
            return None, str(e)
    
    def get_video_info(self, url: str) -> tuple:
        """
        Extract video/playlist info without downloading.
        Returns (info_dict, error_message). If error, info is None.
        """
        # Always use subprocess to ensure code is fresh
        if self._use_subprocess:
            return self._get_video_info_subprocess(url)
        
        if not YoutubeDL:
            return None, "yt-dlp not installed"
        
        opts = self._get_base_options()
        opts["extract_flat"] = "in_playlist"  # Fast playlist extraction
        
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file
        
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # yt-dlp may return None instead of raising exception
                if info is None:
                    return None, "Failed to load video - access denied or video unavailable"
                
                # Check if it's a playlist
                if info.get("_type") == "playlist" or "entries" in info:
                    entries = list(info.get("entries", []))
                    return {
                        "is_playlist": True,
                        "title": info.get("title", "Playlist"),
                        "playlist_count": len(entries),
                        "entries": entries,
                    }, None
                else:
                    # Single video - get full info with FRESH options
                    full_opts = self._get_base_options()
                    full_opts["extract_flat"] = False
                    if self.cookies_file:
                        full_opts["cookiefile"] = self.cookies_file
                    
                    with YoutubeDL(full_opts) as ydl2:
                        full_info = ydl2.extract_info(url, download=False)
                        if full_info is None:
                            return None, "Failed to load video - access denied or video unavailable"
                        full_info["is_playlist"] = False
                        return full_info, None
                        
        except Exception as e:
            error_msg = str(e)
            # Parse common YouTube errors - check most specific first
            if "403" in error_msg or "Forbidden" in error_msg:
                error_msg = "HTTP 403 Forbidden - Please update yt-dlp to the latest version"
            elif "Join this channel" in error_msg:
                error_msg = "This video requires channel membership"
            elif "Private video" in error_msg or "private video" in error_msg.lower():
                error_msg = "This video is private"
            elif "members-only" in error_msg.lower():
                error_msg = "This video requires channel membership"
            elif "Sign in" in error_msg or "login" in error_msg.lower():
                error_msg = "Login required to access this video"
            elif "unavailable" in error_msg.lower():
                error_msg = "This video is unavailable"
            elif "age" in error_msg.lower():
                error_msg = "Age-restricted video - login required"
            elif "copyright" in error_msg.lower():
                error_msg = "Video blocked due to copyright"
            
            return None, error_msg
    
    def get_video_details(self, url: str) -> Optional[dict]:
        """Get full video details (formats, thumbnail, etc.)"""
        if not YoutubeDL:
            return None
        
        opts = self._get_base_options()
        opts["extract_flat"] = False
        
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file
        
        try:
            with YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except:
            return None
    
    def download_video(self, url: str, format_str: str = "bv*+ba/b") -> bool:
        """Download a single video."""
        # Use subprocess mode (preferred)
        if self._use_subprocess:
            return self._download_video_subprocess(url, format_str)
        
        if not YoutubeDL:
            if self._error_callback:
                self._error_callback("yt-dlp not installed")
            return False
        
        if self._cancel_requested:
            return False
        
        try:
            opts = self._get_options(format_str)
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            if self._error_callback:
                self._error_callback(str(e))
            return False
    
    def download_playlist(
        self,
        videos: list[dict],
        format_str: str = "bv*+ba/b"
    ):
        """
        Download multiple videos sequentially.
        Each video dict should have: url, title, thumbnail (optional)
        """
        self._is_downloading = True
        self._cancel_requested = False
        
        for i, video in enumerate(videos):
            if self._cancel_requested:
                break
            
            url = video.get("url") or video.get("webpage_url") or f"https://youtube.com/watch?v={video.get('id', '')}"
            title = video.get("title", f"Video {i+1}")
            thumbnail = video.get("thumbnail", "")
            
            # Notify UI that this video is starting
            if self._video_start_callback:
                self._video_start_callback({
                    "index": i,
                    "total": len(videos),
                    "title": title,
                    "url": url,
                    "thumbnail": thumbnail,
                })
            
            # Download this video
            success = self.download_video(url, format_str)
            
            if not success and not self._cancel_requested:
                # Error already reported via callback
                pass
        
        self._is_downloading = False
    
    def cancel(self):
        """Cancel ongoing downloads."""
        self._cancel_requested = True
        # Terminate subprocess if running
        if self._current_process:
            try:
                self._current_process.terminate()
            except:
                pass
    
    @property
    def is_downloading(self) -> bool:
        return self._is_downloading
