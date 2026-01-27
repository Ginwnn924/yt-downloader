"""
StreamFetch - YouTube Video Downloader
Entry point for the application
"""

import customtkinter as ctk
from app.app import App


def main():
    """Initialize and run the application."""
    # Create and run app (theme managed internally)
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
