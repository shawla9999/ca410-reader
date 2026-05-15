import tkinter as tk
from tkinter import ttk, filedialog

from driver.ca410_types import MeasurementMode, IMAGE_MODES, PEAK_BRIGHTNESS_MODES, LOCAL_DIMMING_MODES, HDR_SDR_MODES
from driver.murideo_driver import (
    CAT_TIMING, CAT_PATTERN, CAT_HDR, CAT_COLOR_SPACE, CAT_COLOR_DEPTH,
    PATTERN_WINDOW, PATTERN_WHITE_SCREEN, PATTERN_BLACK_SCREEN,
    HDR_OFF, HDR_HDR10, HDR_HLG,
)
from ui.fonts import cjk_family
from worker import measurement_worker as mw


class ControlPanel(ttk.LabelFrame):
    """Measurement control buttons and settings."""

    def __init__(self, parent, worker: mw.MeasurementWorker, **kwargs):
        super().__init__(parent, text='控制', **kwargs)
        self._worker = worker
        self._connected = False
        self._continuous_running = False
        self._murideo_connected = False
        self._error_after_id = None
        self._create_widgets()
        self._update_button_states()

    def _create_widgets(self):
        self._measure_btn = ttk.Button(self, text='单次测量', command=self._on_measure)
        self._measure_btn.pack(fill=tk.X, padx=8, pady=(10, 4))

        self._continuous_btn = ttk.Button(
            self, text='开始连续测量', command=self._on_continuous_toggle
        )
        self._continuous_btn.pack(fill=tk.X, padx=8, pady=4)

        self._zero_cal_btn = ttk.Button(self, text='零点校准', command=self._on_zero_cal)
        self._zero_cal_btn.pack(fill=tk.X, padx=8, pady=4)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(self, text='测量模式:').pack(anchor='w', padx=8)
        self._mode_var = tk.IntVar(value=MeasurementMode.XY_LV)
        for mode in MeasurementMode:
            name = 'xyLv' if mode == MeasurementMode.XY_LV else 'TduvLv'
            ttk.Radiobutton(
                self,
                text=name,
                variable=self._mode_var,
                value=mode,
                command=self._on_mode_change,
            ).pack(anchor='w', padx=20)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # -- Murideo WebSocket connection section --
        murideo_frame = ttk.LabelFrame(self, text='Murideo (WebSocket)')
        murideo_frame.pack(fill=tk.X, padx=8, pady=2)

        ip_frame = ttk.Frame(murideo_frame)
        ip_frame.pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(ip_frame, text='IP:').pack(side=tk.LEFT)
        self._murideo_ip_var = tk.StringVar(value='192.168.1.239')
        self._murideo_ip_entry = ttk.Entry(
            ip_frame, textvariable=self._murideo_ip_var, width=14
        )
        self._murideo_ip_entry.pack(side=tk.LEFT, padx=4)

        btn_frame = ttk.Frame(murideo_frame)
        btn_frame.pack(fill=tk.X, padx=4, pady=2)
        self._murideo_connect_btn = ttk.Button(
            btn_frame, text='连接 Murideo', command=self._on_murideo_connect, width=12
        )
        self._murideo_connect_btn.pack(side=tk.LEFT, padx=2)
        self._murideo_status_label = ttk.Label(btn_frame, text='未连接', foreground='gray')
        self._murideo_status_label.pack(side=tk.LEFT, padx=4)

        # Murideo write button (Murideo is write-only)
        set_frame = ttk.Frame(murideo_frame)
        set_frame.pack(fill=tk.X, padx=4, pady=2)
        self._murideo_set_btn = ttk.Button(
            set_frame, text='设置到 Murideo', command=self._on_murideo_set, width=14
        )
        self._murideo_set_btn.pack(side=tk.LEFT, padx=2)
        self._murideo_auto_set_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            set_frame, text='测量时自动设置', variable=self._murideo_auto_set_var,
        ).pack(side=tk.LEFT, padx=4)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Image mode
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(mode_frame, text='图像模式:').pack(side=tk.LEFT)
        self._image_mode_var = tk.StringVar(value=IMAGE_MODES[0])
        self._image_mode_combo = ttk.Combobox(
            mode_frame, textvariable=self._image_mode_var,
            values=IMAGE_MODES, width=6, state='readonly'
        )
        self._image_mode_combo.pack(side=tk.LEFT, padx=4)

        # Small window size (MURIDEO) - combobox with presets + manual input
        ratio_frame = ttk.Frame(self)
        ratio_frame.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(ratio_frame, text='小窗口大小:').pack(side=tk.LEFT)
        self._window_ratio_var = tk.StringVar(value='')
        self._window_ratio_combo = ttk.Combobox(
            ratio_frame, textvariable=self._window_ratio_var,
            values=['10', '20', '30', '40', '50', '60', '70', '80', '90', '100'],
            width=5
        )
        self._window_ratio_combo.pack(side=tk.LEFT, padx=4)
        ttk.Label(ratio_frame, text='%').pack(side=tk.LEFT)

        # HDR/SDR
        hdr_frame = ttk.Frame(self)
        hdr_frame.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(hdr_frame, text='HDR/SDR:').pack(side=tk.LEFT)
        self._hdr_sdr_var = tk.StringVar(value=HDR_SDR_MODES[0])
        self._hdr_sdr_combo = ttk.Combobox(
            hdr_frame, textvariable=self._hdr_sdr_var,
            values=HDR_SDR_MODES, width=5, state='readonly'
        )
        self._hdr_sdr_combo.pack(side=tk.LEFT, padx=4)

        # White block brightness (MURIDEO)
        bright_frame = ttk.Frame(self)
        bright_frame.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(bright_frame, text='IRE Level:').pack(side=tk.LEFT)
        self._window_brightness_var = tk.StringVar(value='')
        self._window_brightness_entry = ttk.Entry(
            bright_frame, textvariable=self._window_brightness_var, width=8
        )
        self._window_brightness_entry.pack(side=tk.LEFT, padx=4)
        ttk.Label(bright_frame, text='(0-255)').pack(side=tk.LEFT)

        # Peak brightness
        peak_frame = ttk.Frame(self)
        peak_frame.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(peak_frame, text='峰值亮度:').pack(side=tk.LEFT)
        self._peak_brightness_var = tk.StringVar(value=PEAK_BRIGHTNESS_MODES[0])
        self._peak_brightness_combo = ttk.Combobox(
            peak_frame, textvariable=self._peak_brightness_var,
            values=PEAK_BRIGHTNESS_MODES, width=4, state='readonly'
        )
        self._peak_brightness_combo.pack(side=tk.LEFT, padx=4)

        # Current backlight value
        bl_frame = ttk.Frame(self)
        bl_frame.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(bl_frame, text='当前背光值:').pack(side=tk.LEFT)
        self._backlight_var = tk.StringVar(value='')
        self._backlight_entry = ttk.Entry(
            bl_frame, textvariable=self._backlight_var, width=8
        )
        self._backlight_entry.pack(side=tk.LEFT, padx=4)

        # Local Dimming
        ld_frame = ttk.Frame(self)
        ld_frame.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(ld_frame, text='Local Dimming:').pack(side=tk.LEFT)
        self._local_dimming_var = tk.StringVar(value=LOCAL_DIMMING_MODES[0])
        self._local_dimming_combo = ttk.Combobox(
            ld_frame, textvariable=self._local_dimming_var,
            values=LOCAL_DIMMING_MODES, width=4, state='readonly'
        )
        self._local_dimming_combo.pack(side=tk.LEFT, padx=4)

        # Note
        note_frame = ttk.Frame(self)
        note_frame.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(note_frame, text='备注:').pack(side=tk.LEFT)
        self._note_var = tk.StringVar(value='')
        self._note_entry = ttk.Entry(
            note_frame, textvariable=self._note_var, width=12
        )
        self._note_entry.pack(side=tk.LEFT, padx=4)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Auto-write to Excel
        excel_frame = ttk.Frame(self)
        excel_frame.pack(fill=tk.X, padx=8, pady=2)
        self._excel_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            excel_frame, text='写入Excel', variable=self._excel_var,
            command=self._on_excel_toggle
        ).pack(side=tk.LEFT)

        # Excel file path
        path_frame = ttk.Frame(self)
        path_frame.pack(fill=tk.X, padx=8, pady=2)
        self._excel_path_var = tk.StringVar(value='')
        self._excel_path_entry = ttk.Entry(
            path_frame, textvariable=self._excel_path_var, width=16
        )
        self._excel_path_entry.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        ttk.Button(path_frame, text='...', width=3, command=self._on_browse_excel).pack(side=tk.LEFT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Interval
        interval_frame = ttk.Frame(self)
        interval_frame.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(interval_frame, text='间隔:').pack(side=tk.LEFT)
        self._interval_var = tk.StringVar(value='1.0')
        self._interval_entry = ttk.Entry(interval_frame, textvariable=self._interval_var, width=6)
        self._interval_entry.pack(side=tk.LEFT, padx=4)
        ttk.Label(interval_frame, text='秒').pack(side=tk.LEFT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # -- Auto-test section --
        at_frame = ttk.LabelFrame(self, text='自动测试')
        at_frame.pack(fill=tk.X, padx=8, pady=2)

        at_btn_frame = ttk.Frame(at_frame)
        at_btn_frame.pack(fill=tk.X, padx=4, pady=2)
        self._autotest_start_btn = ttk.Button(
            at_btn_frame, text='开始自动测试', command=self._on_autotest_start, width=14
        )
        self._autotest_start_btn.pack(side=tk.LEFT, padx=2)
        self._autotest_pause_btn = ttk.Button(
            at_btn_frame, text='暂停', command=self._on_autotest_pause, width=6, state='disabled'
        )
        self._autotest_pause_btn.pack(side=tk.LEFT, padx=2)
        self._autotest_stop_btn = ttk.Button(
            at_btn_frame, text='停止', command=self._on_autotest_stop, width=6, state='disabled'
        )
        self._autotest_stop_btn.pack(side=tk.LEFT, padx=2)

        self._autotest_progress_var = tk.StringVar(value='')
        self._autotest_progress_label = ttk.Label(
            at_frame, textvariable=self._autotest_progress_var, font=(cjk_family(), 9)
        )
        self._autotest_progress_label.pack(fill=tk.X, padx=4, pady=2)

        self._autotest_case_var = tk.StringVar(value='')
        self._autotest_case_label = ttk.Label(
            at_frame, textvariable=self._autotest_case_var,
            font=(cjk_family(), 9), foreground='#0066CC', wraplength=180
        )
        self._autotest_case_label.pack(fill=tk.X, padx=4, pady=(0, 4))

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        self._error_label = ttk.Label(self, text='', foreground='red', wraplength=160, font=(cjk_family(), 9))
        self._error_label.pack(fill=tk.X, padx=8, pady=4)

    # -- public state methods ------------------------------------------------

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        self._update_button_states()

    def set_continuous_running(self, running: bool) -> None:
        self._continuous_running = running
        self._continuous_btn.config(
            text='停止连续测量' if running else '开始连续测量'
        )
        self._update_button_states()

    def set_murideo_connected(self, connected: bool) -> None:
        self._murideo_connected = connected
        self._murideo_status_label.config(
            text='已连接' if connected else '未连接',
            foreground='#00CC00' if connected else 'gray',
        )
        self._murideo_connect_btn.config(
            text='断开 Murideo' if connected else '连接 Murideo'
        )
        self._update_button_states()

    def show_error(self, message: str) -> None:
        self._error_label.config(text=message)
        if self._error_after_id:
            self.after_cancel(self._error_after_id)
        self._error_after_id = self.after(5000, lambda: self._error_label.config(text=''))

    # -- getter methods for measurement metadata -----------------------------

    def get_mode(self) -> MeasurementMode:
        return MeasurementMode(self._mode_var.get())

    def get_image_mode(self) -> str:
        return self._image_mode_var.get()

    def get_window_ratio(self) -> float | None:
        try:
            val = float(self._window_ratio_var.get())
            if 0 <= val <= 100:
                return val
            return None
        except ValueError:
            return None

    def get_window_brightness(self) -> float | None:
        try:
            val = float(self._window_brightness_var.get())
            return val if val >= 0 else None
        except ValueError:
            return None

    def get_peak_brightness(self) -> str:
        return self._peak_brightness_var.get()

    def get_backlight_value(self) -> float | None:
        try:
            val = float(self._backlight_var.get())
            return val if val >= 0 else None
        except ValueError:
            return None

    def get_local_dimming(self) -> str:
        return self._local_dimming_var.get()

    def get_hdr_sdr(self) -> str:
        return self._hdr_sdr_var.get()

    def get_note(self) -> str:
        return self._note_var.get()

    def is_excel_write_enabled(self) -> bool:
        return self._excel_var.get()

    def get_excel_path(self) -> str:
        return self._excel_path_var.get()

    def is_murideo_auto_set(self) -> bool:
        return self._murideo_auto_set_var.get()

    # -- Murideo config getters/setters --------------------------------------

    def get_murideo_host(self) -> str:
        return self._murideo_ip_var.get().strip()

    def set_murideo_host(self, host: str) -> None:
        self._murideo_ip_var.set(host)

    def set_window_ratio_value(self, value: float) -> None:
        self._window_ratio_var.set(f'{value:.0f}')

    def set_window_brightness_value(self, value: float) -> None:
        self._window_brightness_var.set(f'{value:.0f}')

    def set_test_case_fields(self, case) -> None:
        """Populate all UI fields from a TestCase object."""
        self._image_mode_var.set(case.image_mode)
        self._peak_brightness_var.set(case.peak_brightness)
        self._backlight_var.set(f'{case.backlight_value:.0f}')
        self._local_dimming_var.set(case.local_dimming)
        self._window_ratio_var.set(f'{case.window_size:.0f}')
        self._hdr_sdr_var.set(case.hdr_sdr)
        self._window_brightness_var.set(f'{case.window_brightness:.0f}')
        self._note_var.set(case.note)

    def set_autotest_progress(self, index: int, total: int, case=None) -> None:
        self._autotest_progress_var.set(f'进度: {index + 1}/{total}')
        if case:
            self._autotest_case_var.set(
                f'{case.test_id}: {case.image_mode} / {case.hdr_sdr} / '
                f'窗口{case.window_size:.0f}% / IRE{case.window_brightness:.0f} / '
                f'峰值{case.peak_brightness} / LD{case.local_dimming}'
            )

    def set_autotest_state(self, running: bool, paused: bool = False) -> None:
        self._autotest_start_btn.config(
            state='disabled' if running else 'normal'
        )
        self._autotest_pause_btn.config(
            state='normal' if running and not paused else 'disabled',
            text='继续' if paused else '暂停'
        )
        self._autotest_stop_btn.config(
            state='normal' if running else 'disabled'
        )

    # -- callbacks (to be set by MainWindow) ---------------------------------

    _murideo_connect_callback = None
    _murideo_disconnect_callback = None
    _murideo_set_callback = None
    _autotest_start_callback = None
    _autotest_pause_callback = None
    _autotest_stop_callback = None

    def set_murideo_connect_callback(self, callback) -> None:
        self._murideo_connect_callback = callback

    def set_murideo_disconnect_callback(self, callback) -> None:
        self._murideo_disconnect_callback = callback

    def set_murideo_set_callback(self, callback) -> None:
        self._murideo_set_callback = callback

    def set_autotest_start_callback(self, callback) -> None:
        self._autotest_start_callback = callback

    def set_autotest_pause_callback(self, callback) -> None:
        self._autotest_pause_callback = callback

    def set_autotest_stop_callback(self, callback) -> None:
        self._autotest_stop_callback = callback

    # -- Excel ---------------------------------------------------------------

    def _on_excel_toggle(self) -> None:
        if self._excel_var.get() and not self._excel_path_var.get():
            self._on_browse_excel()

    def _on_browse_excel(self) -> None:
        filepath = filedialog.askopenfilename(
            parent=self,
            filetypes=[('Excel 文件', '*.xlsx'), ('所有文件', '*.*')],
            title='选择测试用例Excel文件',
        )
        if filepath:
            self._excel_path_var.set(filepath)

    def get_interval(self) -> float:
        try:
            val = float(self._interval_var.get())
            return max(0.1, val)
        except ValueError:
            return 1.0

    # -- internal ------------------------------------------------------------

    def _update_button_states(self) -> None:
        self._measure_btn.config(state='normal' if self._connected and not self._continuous_running else 'disabled')
        self._continuous_btn.config(state='normal' if self._connected else 'disabled')
        self._zero_cal_btn.config(state='normal' if self._connected and not self._continuous_running else 'disabled')
        self._murideo_set_btn.config(state='normal')

    def _on_measure(self) -> None:
        self._worker.measure_single(mode=self.get_mode())

    def _on_continuous_toggle(self) -> None:
        if self._continuous_running:
            self._worker.stop_continuous()
            self.set_continuous_running(False)
        else:
            self._worker.start_continuous(interval=self.get_interval(), mode=self.get_mode())
            self.set_continuous_running(True)

    def _on_zero_cal(self) -> None:
        self._worker.zero_calibrate()

    def _on_mode_change(self) -> None:
        if self._connected:
            self._worker.set_mode(self.get_mode())

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

    def _on_autotest_start(self) -> None:
        if self._autotest_start_callback:
            self._autotest_start_callback()

    def _on_autotest_pause(self) -> None:
        if self._autotest_pause_callback:
            self._autotest_pause_callback()

    def _on_autotest_stop(self) -> None:
        if self._autotest_stop_callback:
            self._autotest_stop_callback()
