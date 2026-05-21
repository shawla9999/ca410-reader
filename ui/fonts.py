"""Auto-detect suitable fonts for CJK text display in tkinter."""

import logging
import sys
import tkinter as tk
from tkinter import font as tkfont

logger = logging.getLogger(__name__)


def _detect_fonts(root: tk.Tk) -> tuple[str, str]:
    """Return (cjk_font_family, mono_font_family) that support Chinese.

    On Windows, tkinter uses Chinese font names (e.g. '微软雅黑' not 'Microsoft YaHei').
    On Linux, both English and localized names may appear in font.families().
    """
    families = set(tkfont.families(root))

    # Ordered by preference - best CJK font first
    # Windows names come in both English and Chinese forms depending on locale;
    # we try both to cover all cases
    cjk_candidates = [
        # Windows
        ('微软雅黑', 'Microsoft YaHei'),
        ('黑体', 'SimHei'),
        ('宋体', 'SimSun'),
        ('仿宋', 'FangSong'),
        ('楷体', 'KaiTi'),
        # Cross-platform
        ('Noto Sans CJK SC', 'Noto Sans CJK SC'),
        ('Noto Sans CJK TC', 'Noto Sans CJK TC'),
        # Linux
        ('WenQuanYi Micro Hei', 'WenQuanYi Micro Hei'),
        ('WenQuanYi Zen Hei', 'WenQuanYi Zen Hei'),
        ('Droid Sans Fallback', 'Droid Sans Fallback'),
        ('AR PL UMing CN', 'AR PL UMing CN'),
    ]

    mono_candidates = [
        # Windows
        ('Consolas', 'Consolas'),
        ('Courier New', 'Courier New'),
        # Cross-platform CJK mono
        ('Noto Sans Mono CJK SC', 'Noto Sans Mono CJK SC'),
        ('WenQuanYi Micro Hei Mono', 'WenQuanYi Micro Hei Mono'),
    ]

    cjk = ''
    for cn_name, en_name in cjk_candidates:
        # Try both Chinese and English names
        if cn_name in families:
            cjk = cn_name
            break
        if en_name != cn_name and en_name in families:
            cjk = en_name
            break

    mono = ''
    for cn_name, en_name in mono_candidates:
        if cn_name in families:
            mono = cn_name
            break
        if en_name != cn_name and en_name in families:
            mono = en_name
            break

    if not cjk:
        # Last resort: scan for any font with CJK hints
        for f in sorted(families):
            fl = f.lower()
            if any(k in fl for k in ['cjk', 'yahei', 'simhei', 'simsun', 'heiti',
                                       'songti', 'wenquanyi', 'noto sans cjk']):
                cjk = f
                break

    if not mono and cjk:
        mono = cjk

    # Final fallback - use system default which handles CJK via substitution
    if not cjk:
        cjk = 'TkDefaultFont'
    if not mono:
        mono = 'TkFixedFont'

    logger.info('Font detection: CJK=%s, Mono=%s, platform=%s', cjk, mono, sys.platform)
    return cjk, mono


_cache: dict[str, str] = {}


def init(root: tk.Tk) -> None:
    """Initialize font cache. Must be called after creating Tk root."""
    cjk, mono = _detect_fonts(root)
    _cache['cjk'] = cjk
    _cache['mono'] = mono


def cjk_family() -> str:
    return _cache.get('cjk', 'TkDefaultFont')


def mono_family() -> str:
    return _cache.get('mono', 'TkFixedFont')


def value_font(size: int = 24) -> tuple:
    return (mono_family(), size)


def label_font(size: int = 10) -> tuple:
    return (cjk_family(), size)


def unit_font(size: int = 9) -> tuple:
    return (cjk_family(), size)
