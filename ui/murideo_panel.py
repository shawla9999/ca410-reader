import tkinter as tk
from tkinter import ttk

from driver.ca410_types import HDR_SDR_MODES
from driver.murideo_driver import (
    HDR_OFF, HDR_HDR10, HDR_HLG,
)
from ui.fonts import cjk_family
from util.profile import load_profile, list_profiles


class MurideoPanel(ttk.LabelFrame):
    """Murideo device control panel: connection, HDR, window, IRE, timing, color space, pattern."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text='Murideo 控制', **kwargs)
        self._murideo_connected = False
        self._profile_paths = {}
        self._create_widgets()

    def _create_widgets(self):
        # -- Connection --
        conn_frame = ttk.Frame(self)
        conn_frame.pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(conn_frame, text='IP:').pack(side=tk.LEFT)
        self._murideo_ip_var = tk.StringVar(value='192.168.1.239')
        ttk.Entry(conn_frame, textvariable=self._murideo_ip_var, width=14).pack(side=tk.LEFT, padx=4)
        self._murideo_connect_btn = ttk.Button(
            conn_frame, text='连接', command=self._on_murideo_connect, width=6
        )
        self._murideo_connect_btn.pack(side=tk.LEFT, padx=2)
        self._murideo_status_label = ttk.Label(conn_frame, text='未连接', foreground='gray')
        self._murideo_status_label.pack(side=tk.LEFT, padx=4)

        # -- Set button --
        set_frame = ttk.Frame(self)
        set_frame.pack(fill=tk.X, padx=4, pady=2)
        self._murideo_set_btn = ttk.Button(
            set_frame, text='设置到 Murideo', command=self._on_murideo_set, width=14
        )
        self._murideo_set_btn.pack(side=tk.LEFT, padx=2)
        self._murideo_auto_set_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            set_frame, text='测量时自动设置', variable=self._murideo_auto_set_var,
        ).pack(side=tk.LEFT, padx=4)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=4)

        # -- HDR/SDR --
        hdr_frame = ttk.Frame(self)
        hdr_frame.pack(fill=tk.X, padx=4, pady=1)
        ttk.Label(hdr_frame, text='HDR/SDR:').pack(side=tk.LEFT)
        self._hdr_sdr_var = tk.StringVar(value=HDR_SDR_MODES[0])
        ttk.Combobox(
            hdr_frame, textvariable=self._hdr_sdr_var,
            values=HDR_SDR_MODES, width=5, state='readonly'
        ).pack(side=tk.LEFT, padx=4)

        # -- Window size --
        ws_frame = ttk.Frame(self)
        ws_frame.pack(fill=tk.X, padx=4, pady=1)
        ttk.Label(ws_frame, text='窗口大小:').pack(side=tk.LEFT)
        self._window_ratio_var = tk.StringVar(value='')
        ttk.Combobox(
            ws_frame, textvariable=self._window_ratio_var,
            values=['10', '20', '30', '40', '50', '60', '70', '80', '90', '100'],
            width=5
        ).pack(side=tk.LEFT, padx=4)
        ttk.Label(ws_frame, text='%').pack(side=tk.LEFT)

        # -- IRE Level --
        ire_frame = ttk.Frame(self)
        ire_frame.pack(fill=tk.X, padx=4, pady=1)
        ttk.Label(ire_frame, text='IRE Level:').pack(side=tk.LEFT)
        self._window_brightness_var = tk.StringVar(value='')
        ttk.Entry(ire_frame, textvariable=self._window_brightness_var, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Label(ire_frame, text='(0-255)').pack(side=tk.LEFT)

        # -- Timing --
        timing_frame = ttk.Frame(self)
        timing_frame.pack(fill=tk.X, padx=4, pady=1)
        ttk.Label(timing_frame, text='信号格式:').pack(side=tk.LEFT)
        self._timing_var = tk.StringVar(value='34')
        self._timing_combo = ttk.Combobox(
            timing_frame, textvariable=self._timing_var, width=16, state='readonly',
            values=[
                '34=3840x2160@60Hz', '35=3840x2160@59.94Hz', '36=3840x2160@50Hz',
                '28=3840x2160@30Hz', '31=3840x2160@24Hz',
                '20=1080p@60Hz', '21=1080p@59.94Hz', '27=1080p@50Hz',
                '115=7680x4320@60Hz', '110=7680x4320@30Hz',
            ],
        )
        self._timing_combo.pack(side=tk.LEFT, padx=4)

        # -- Color space --
        cs_frame = ttk.Frame(self)
        cs_frame.pack(fill=tk.X, padx=4, pady=1)
        ttk.Label(cs_frame, text='色彩空间:').pack(side=tk.LEFT)
        self._color_space_var = tk.StringVar(value='0=RGB(0-255)')
        self._color_space_combo = ttk.Combobox(
            cs_frame, textvariable=self._color_space_var, width=12, state='readonly',
            values=[
                '0=RGB(0-255)', '1=RGB(16-235)', '2=YC444', '3=YC422', '4=YC420',
            ],
        )
        self._color_space_combo.pack(side=tk.LEFT, padx=4)

        # -- Pattern --
        pat_frame = ttk.Frame(self)
        pat_frame.pack(fill=tk.X, padx=4, pady=1)
        ttk.Label(pat_frame, text='测试图案:').pack(side=tk.LEFT)
        self._pattern_var = tk.StringVar(value='26=Window')
        self._pattern_combo = ttk.Combobox(
            pat_frame, textvariable=self._pattern_var, width=16, state='readonly',
            values=[
                '26=Window', '11=White', '10=Black', '0=100%ColorBars',
                '4=Red', '5=Green', '6=Blue', '50=DVS White1',
                '51=DVS White2', '52=DVS White3', '53=DVS White80-100',
            ],
        )
        self._pattern_combo.pack(side=tk.LEFT, padx=4)

    # -- state methods --

    def set_murideo_connected(self, connected: bool) -> None:
        self._murideo_connected = connected
        self._murideo_status_label.config(
            text='已连接' if connected else '未连接',
            foreground='#00CC00' if connected else 'gray',
        )
        self._murideo_connect_btn.config(
            text='断开' if connected else '连接'
        )

    # -- getters --

    def get_murideo_host(self) -> str:
        return self._murideo_ip_var.get().strip()

    def set_murideo_host(self, host: str) -> None:
        self._murideo_ip_var.set(host)

    def get_hdr_sdr(self) -> str:
        return self._hdr_sdr_var.get()

    def get_window_ratio(self) -> float | None:
        try:
            val = float(self._window_ratio_var.get())
            return val if 0 <= val <= 100 else None
        except ValueError:
            return None

    def get_window_brightness(self) -> float | None:
        try:
            val = float(self._window_brightness_var.get())
            return val if val >= 0 else None
        except ValueError:
            return None

    def get_timing(self) -> int | None:
        try:
            return int(self._timing_var.get().split('=')[0])
        except (ValueError, IndexError):
            return None

    def get_color_space(self) -> int | None:
        try:
            return int(self._color_space_var.get().split('=')[0])
        except (ValueError, IndexError):
            return None

    def get_pattern(self) -> int | None:
        try:
            return int(self._pattern_var.get().split('=')[0])
        except (ValueError, IndexError):
            return None

    def is_murideo_auto_set(self) -> bool:
        return self._murideo_auto_set_var.get()

    def set_window_ratio_value(self, value: float) -> None:
        self._window_ratio_var.set(f'{value:.0f}')

    def set_window_brightness_value(self, value: float) -> None:
        self._window_brightness_var.set(f'{value:.0f}')

    def set_timing_value(self, timing_id: int) -> None:
        for item in self._timing_combo['values']:
            if item.startswith(f'{timing_id}='):
                self._timing_var.set(item)
                return
        self._timing_var.set(str(timing_id))

    def set_color_space_value(self, cs_id: int) -> None:
        for item in self._color_space_combo['values']:
            if item.startswith(f'{cs_id}='):
                self._color_space_var.set(item)
                return
        self._color_space_var.set(str(cs_id))

    def set_pattern_value(self, pat_id: int) -> None:
        for item in self._pattern_combo['values']:
            if item.startswith(f'{pat_id}='):
                self._pattern_var.set(item)
                return
        self._pattern_var.set(str(pat_id))

    # -- callbacks --

    _murideo_connect_callback = None
    _murideo_disconnect_callback = None
    _murideo_set_callback = None

    def set_murideo_connect_callback(self, callback) -> None:
        self._murideo_connect_callback = callback

    def set_murideo_disconnect_callback(self, callback) -> None:
        self._murideo_disconnect_callback = callback

    def set_murideo_set_callback(self, callback) -> None:
        self._murideo_set_callback = callback

    # -- internal --

    def _on_murideo_connect(self) -> None:
        if self._murideo_connected:
            if self._murideo_disconnect_callback:
                self._murideo_disconnect_callback()
        else:
            if self._murideo_connect_callback:
                self._murideo_connect_callback()

    def _on_murideo_set(self) -> None:
        if self._murideo_set_callback:
            self._murideo_set_callback()
