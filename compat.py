"""Small cross-platform helpers shared by every script (Windows, macOS, Linux)."""
import os
import sys

for _s in (sys.stdout, sys.stderr):                 # Windows consoles default to a legacy code page; Vietnamese needs UTF-8
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def fonts_dir():
    """Folder with the system fonts (ffmpeg's ass filter looks here for Arial)."""
    if sys.platform == "win32":
        return os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts").replace("\\", "/")
    if sys.platform == "darwin":
        return "/System/Library/Fonts/Supplemental"      # Arial lives here on macOS
    return "/usr/share/fonts"


def ass_filter(path):
    """ffmpeg filter fragment that burns an .ass file in, with the fonts folder escaped for the filtergraph."""
    return f"ass={path}:fontsdir=" + fonts_dir().replace(":", "\\\\:")
