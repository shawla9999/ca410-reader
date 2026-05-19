"""Path utilities for PyInstaller compatibility."""

import os
import sys


def resource_path(relative: str) -> str:
    """Return absolute path to a resource, working both in dev and when frozen by PyInstaller."""
    if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath('.'), relative)
