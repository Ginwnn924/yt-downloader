"""
Theme Configuration - Custom Colors with Neon Accents
"""

import customtkinter as ctk
import tkinter.font as tkfont


# ============================================================
# FONT CONFIGURATION
# ============================================================

FONT_FAMILY = "Segoe UI"


def init_fonts() -> str:
    """Initialize fonts after Tk is ready."""
    global FONT_FAMILY
    
    preferred = ["Inter", "Segoe UI", "SF Pro Display", "Helvetica Neue", "Roboto"]
    
    try:
        available = set(tkfont.families())
        for font in preferred:
            if font in available:
                FONT_FAMILY = font
                break
    except:
        pass
    
    return FONT_FAMILY


# ============================================================
# TYPOGRAPHY
# ============================================================

FONT_SIZE_SM = 12    # Body text, inputs, buttons
FONT_SIZE_MD = 14    # Section titles
FONT_SIZE_LG = 18    # Page title


def font(size: int = FONT_SIZE_SM, bold: bool = False) -> ctk.CTkFont:
    """Create font with current font family."""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight="bold" if bold else "normal")


# ============================================================
# SPACING
# ============================================================

PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 20


# ============================================================
# DARK THEME - Custom Colors with Neon Accents
# ============================================================

DARK = {
    # Backgrounds
    "bg_app": "#15181d",          # Main app background (custom)
    "bg_card": "#1c2027",         # Card panels
    "bg_input": "#252a33",        # Input fields
    "bg_hover": "#2f3542",        # Hover states
    
    # Text
    "text": "#ffffff",            # Primary text
    "text_dim": "#9ca3af",        # Secondary
    "text_muted": "#6b7280",      # Hints
    
    # Borders
    "border": "#2f3542",
    
    # Custom accent colors
    "green": "#2ec772",           # Custom green
    "green_hover": "#26a861",     # Darker green
    "blue": "#3884f1",            # Custom blue
    "blue_hover": "#2d6ed4",      # Darker blue
    "red": "#f87171",             # Error
    "red_hover": "#ef4444",
    "yellow": "#fbbf24",          # Warning
    
    # Neon colors for progress
    "neon_green": "#2ec772",      # Neon green
    "neon_blue": "#3884f1",       # Neon blue
    "neon_cyan": "#22d3ee",       # Neon cyan
    "neon_purple": "#a855f7",     # Neon purple
    "neon_pink": "#ec4899",       # Neon pink
}


# ============================================================
# LIGHT THEME
# ============================================================

LIGHT = {
    # Backgrounds
    "bg_app": "#f4f6f9",
    "bg_card": "#ffffff",
    "bg_input": "#ebeef3",
    "bg_hover": "#dce0e6",
    
    # Text
    "text": "#1a1f26",
    "text_dim": "#5c6773",
    "text_muted": "#9ca3af",
    
    # Borders
    "border": "#dce0e6",
    
    # Accent (same as dark)
    "green": "#2ec772",
    "green_hover": "#26a861",
    "blue": "#3884f1",
    "blue_hover": "#2d6ed4",
    "red": "#dc2626",
    "red_hover": "#b91c1c",
    "yellow": "#ca8a04",
    
    # Neon (same)
    "neon_green": "#2ec772",
    "neon_blue": "#3884f1",
    "neon_cyan": "#06b6d4",
    "neon_purple": "#9333ea",
    "neon_pink": "#db2777",
}


def theme(mode: str = "dark") -> dict:
    """Get theme dict by mode."""
    return DARK if mode == "dark" else LIGHT
