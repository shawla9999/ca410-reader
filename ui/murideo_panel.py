import tkinter as tk
from tkinter import ttk

import serial.tools.list_ports

from driver.ca410_types import HDR_SDR_MODES
from driver.murideo_driver import (
    HDR_OFF, HDR_HDR10, HDR_HLG,
)
from ui.fonts import cjk_family
from util.profile import load_profile, list_profiles


class MurideoPanel(ttk.LabelFrame):
    """Murideo device control panel: connection, HDR, window, IRE, timing, color space, pattern."""

    TRANSPORT_OPTIONS = ['WebSocket', 'Serial']
    BAUDRATE_OPTIONS = ['9600', '19200', '38400', '57600', '115200', '230400', '460800']

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text='Murideo 控制', **kwargs)
        self._murideo_connected = False
        self._profile_paths = {}
        self._create_widgets()

    def _create_widgets(self):
        # -- Transport type selector --
        transport_frame = ttk.Frame(self)
        transport_frame.pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(transport_frame, text='连接方式:').pack(side=tk.LEFT)
        self._transport_var = tk.StringVar(value=self.TRANSPORT_OPTIONS[0])
        self._transport_combo = ttk.Combobox(
            transport_frame, textvariable=self._transport_var,
            values=self.TRANSPORT_OPTIONS, width=10, state='readonly',
        )
        self._transport_combo.pack(side=tk.LEFT, padx=4)
        self._transport_combo.bind('<<ComboboxSelected>>', self._on_transport_change)

        # -- WebSocket connection frame --
        self._ws_frame = ttk.Frame(self)
        self._ws_frame.pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(self._ws_frame, text='IP:').pack(side=tk.LEFT)
        self._murideo_ip_var = tk.StringVar(value='192.168.1.239')
        ttk.Entry(self._ws_frame, textvariable=self._murideo_ip_var, width=14).pack(side=tk.LEFT, padx=4)
        self._ws_connect_btn = ttk.Button(
            self._ws_frame, text='连接', command=self._on_murideo_connect, width=6,
        )
        self._ws_connect_btn.pack(side=tk.LEFT, padx=2)
        self._ws_status_label = ttk.Label(self._ws_frame, text='未连接', foreground='gray')
        self._ws_status_label.pack(side=tk.LEFT, padx=4)

        # -- Serial connection frame (hidden by default) --
        self._serial_frame = ttk.Frame(self)
        # Port row
        serial_port_frame = ttk.Frame(self._serial_frame)
        serial_port_frame.pack(fill=tk.X, pady=1)
        ttk.Label(serial_port_frame, text='端口:').pack(side=tk.LEFT)
        self._serial_port_var = tk.StringVar()
        self._serial_port_combo = ttk.Combobox(
            serial_port_frame, textvariable=self._serial_port_var,
            width=22, state='readonly',
        )
        self._serial_port_combo.pack(side=tk.LEFT, padx=4)
        ttk.Button(
            serial_port_frame, text='刷新', command=self._refresh_serial_ports, width=4,
        ).pack(side=tk.LEFT, padx=2)
        # Baudrate row
        serial_baud_frame = ttk.Frame(self._serial_frame)
        serial_baud_frame.pack(fill=tk.X, pady=1)
        ttk.Label(serial_baud_frame, text='波特率:').pack(side=tk.LEFT)
        self._baudrate_var = tk.StringVar(value='115200')
        ttk.Combobox(
            serial_baud_frame, textvariable=self._baudrate_var,
            values=self.BAUDRATE_OPTIONS, width=8,
        ).pack(side=tk.LEFT, padx=4)
        # Connect row
        serial_conn_frame = ttk.Frame(self._serial_frame)
        serial_conn_frame.pack(fill=tk.X, pady=1)
        self._serial_connect_btn = ttk.Button(
            serial_conn_frame, text='连接', command=self._on_murideo_connect, width=6,
        )
        self._serial_connect_btn.pack(side=tk.LEFT, padx=2)
        self._serial_status_label = ttk.Label(serial_conn_frame, text='未连接', foreground='gray')
        self._serial_status_label.pack(side=tk.LEFT, padx=4)

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

        # -- Color depth --
        cd_frame = ttk.Frame(self)
        cd_frame.pack(fill=tk.X, padx=4, pady=1)
        ttk.Label(cd_frame, text='色深:').pack(side=tk.LEFT)
        self._color_depth_var = tk.StringVar(value='1=10bit')
        self._color_depth_combo = ttk.Combobox(
            cd_frame, textvariable=self._color_depth_var, width=10, state='readonly',
            values=['0=8bit', '1=10bit', '2=12bit', '3=16bit'],
        )
        self._color_depth_combo.pack(side=tk.LEFT, padx=4)

    # -- transport switching -------------------------------------------------

    def _on_transport_change(self, event=None) -> None:
        if self._murideo_connected:
            return
        transport = self._transport_var.get()
        if transport == 'WebSocket':
            self._serial_frame.pack_forget()
            self._ws_frame.pack(fill=tk.X, padx=4, pady=2)
        else:
            self._ws_frame.pack_forget()
            self._serial_frame.pack(fill=tk.X, padx=4, pady=2)
            self._refresh_serial_ports()

    def _refresh_serial_ports(self) -> None:
        ports = sorted(serial.tools.list_ports.comports(), key=lambda p: p.device)
        values = []
        for p in ports:
            desc = p.description or ''
            mfg = p.manufacturer or ''
            # Tag known non-Murideo devices to help user avoid wrong port
            tag = ''
            dl = desc.lower()
            ml = mfg.lower()
            if ('measuring' in dl or 'konica' in dl or 'ca-410' in dl
                    or 'ca-s40' in dl or 'konica' in ml):
                tag = ' [CA-410]'
            elif 'usb serial' in dl and 'murideo' not in dl:
                tag = ' [USB Serial]'
            values.append(f'{p.device} - {desc}{tag}')
        self._serial_port_combo['values'] = values
        if values:
            self._serial_port_combo.current(0)

    # -- state methods -------------------------------------------------------

    def set_murideo_connected(self, connected: bool) -> None:
        self._murideo_connected = connected
        status_text = '已连接' if connected else '未连接'
        status_color = '#00CC00' if connected else 'gray'
        btn_text = '断开' if connected else '连接'
        self._ws_status_label.config(text=status_text, foreground=status_color)
        self._serial_status_label.config(text=status_text, foreground=status_color)
        self._ws_connect_btn.config(text=btn_text)
        self._serial_connect_btn.config(text=btn_text)

    # -- getters -------------------------------------------------------------

    def get_murideo_transport(self) -> str:
        val = self._transport_var.get()
        return 'websocket' if val == 'WebSocket' else 'serial'

    def get_murideo_host(self) -> str:
        return self._murideo_ip_var.get().strip()

    def get_murideo_serial_port(self) -> str:
        text = self._serial_port_var.get()
        if ' - ' in text:
            return text.split(' - ')[0]
        return text.strip()

    def get_murideo_serial_baudrate(self) -> int:
        try:
            return int(self._baudrate_var.get())
        except ValueError:
            return 115200

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

    def get_color_depth(self) -> int | None:
        try:
            return int(self._color_depth_var.get().split('=')[0])
        except (ValueError, IndexError):
            return None

    def is_murideo_auto_set(self) -> bool:
        return self._murideo_auto_set_var.get()

    # -- setters for external control ----------------------------------------

    def set_murideo_transport(self, transport: str) -> None:
        if transport == 'serial':
            self._transport_var.set('Serial')
            self._ws_frame.pack_forget()
            self._serial_frame.pack(fill=tk.X, padx=4, pady=2)
        else:
            self._transport_var.set('WebSocket')
            self._serial_frame.pack_forget()
            self._ws_frame.pack(fill=tk.X, padx=4, pady=2)

    def set_murideo_serial_port(self, port: str) -> None:
        for item in self._serial_port_combo['values']:
            if item.startswith(port):
                self._serial_port_var.set(item)
                return
        self._serial_port_var.set(port)

    def set_murideo_serial_baudrate(self, baudrate: int) -> None:
        self._baudrate_var.set(str(baudrate))

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

    def set_color_depth_value(self, depth_id: int) -> None:
        for item in self._color_depth_combo['values']:
            if item.startswith(f'{depth_id}='):
                self._color_depth_var.set(item)
                return
        self._color_depth_var.set(str(depth_id))

    # -- callbacks -----------------------------------------------------------

    _murideo_connect_callback = None
    _murideo_disconnect_callback = None
    _murideo_set_callback = None

    def set_murideo_connect_callback(self, callback) -> None:
        self._murideo_connect_callback = callback

    def set_murideo_disconnect_callback(self, callback) -> None:
        self._murideo_disconnect_callback = callback

    def set_murideo_set_callback(self, callback) -> None:
        self._murideo_set_callback = callback

    # -- internal ------------------------------------------------------------

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
