import tkinter as tk
from tkinter import ttk, filedialog

from driver.ca410_types import MeasurementMode, IMAGE_MODES, PEAK_BRIGHTNESS_MODES, LOCAL_DIMMING_MODES, HDR_SDR_MODES
from ui.fonts import cjk_family
from worker import measurement_worker as mw
from util.profile import load_profile, list_profiles


class ControlPanel(ttk.LabelFrame):
    """Measurement controls, TV parameters, profile, and auto-test."""

    def __init__(self, parent, worker: mw.MeasurementWorker, **kwargs):
        super().__init__(parent, text='控制', **kwargs)
        self._worker = worker
        self._connected = False
        self._continuous_running = False
        self._error_after_id = None
        self._profile_paths = {}
        self._create_widgets()
        self._update_button_states()

    def _create_widgets(self):
        # -- Measure buttons --
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=8, pady=(8, 4))
        self._measure_btn = ttk.Button(btn_frame, text='单次测量', command=self._on_measure, width=8)
        self._measure_btn.pack(side=tk.LEFT, padx=2)
        self._continuous_btn = ttk.Button(btn_frame, text='连续测量', command=self._on_continuous_toggle, width=8)
        self._continuous_btn.pack(side=tk.LEFT, padx=2)
        self._zero_cal_btn = ttk.Button(btn_frame, text='零点校准', command=self._on_zero_cal, width=8)
        self._zero_cal_btn.pack(side=tk.LEFT, padx=2)

        # Mode + interval on same row
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, padx=8, pady=2)
        self._mode_var = tk.IntVar(value=MeasurementMode.XY_LV)
        for mode in MeasurementMode:
            name = 'xyLv' if mode == MeasurementMode.XY_LV else 'TduvLv'
            ttk.Radiobutton(mode_frame, text=name, variable=self._mode_var,
                            value=mode, command=self._on_mode_change).pack(side=tk.LEFT, padx=2)
        ttk.Label(mode_frame, text='间隔:').pack(side=tk.LEFT, padx=(8, 2))
        self._interval_var = tk.StringVar(value='1.0')
        ttk.Entry(mode_frame, textvariable=self._interval_var, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(mode_frame, text='秒').pack(side=tk.LEFT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        # -- TV parameters --
        tv_frame = ttk.LabelFrame(self, text='TV 参数')
        tv_frame.pack(fill=tk.X, padx=4, pady=2)

        # Image mode + Peak brightness on same row
        row1 = ttk.Frame(tv_frame)
        row1.pack(fill=tk.X, padx=4, pady=1)
        ttk.Label(row1, text='图像模式:').pack(side=tk.LEFT)
        self._image_mode_var = tk.StringVar(value=IMAGE_MODES[0])
        ttk.Combobox(row1, textvariable=self._image_mode_var,
                      values=IMAGE_MODES, width=6, state='readonly').pack(side=tk.LEFT, padx=4)
        ttk.Label(row1, text='峰值亮度:').pack(side=tk.LEFT, padx=(8, 0))
        self._peak_brightness_var = tk.StringVar(value=PEAK_BRIGHTNESS_MODES[0])
        ttk.Combobox(row1, textvariable=self._peak_brightness_var,
                      values=PEAK_BRIGHTNESS_MODES, width=4, state='readonly').pack(side=tk.LEFT, padx=4)

        # Backlight + Local Dimming on same row
        row2 = ttk.Frame(tv_frame)
        row2.pack(fill=tk.X, padx=4, pady=1)
        ttk.Label(row2, text='背光值:').pack(side=tk.LEFT)
        self._backlight_var = tk.StringVar(value='')
        ttk.Entry(row2, textvariable=self._backlight_var, width=6).pack(side=tk.LEFT, padx=4)
        ttk.Label(row2, text='LD:').pack(side=tk.LEFT, padx=(8, 0))
        self._local_dimming_var = tk.StringVar(value=LOCAL_DIMMING_MODES[0])
        ttk.Combobox(row2, textvariable=self._local_dimming_var,
                      values=LOCAL_DIMMING_MODES, width=4, state='readonly').pack(side=tk.LEFT, padx=4)

        # Note
        row3 = ttk.Frame(tv_frame)
        row3.pack(fill=tk.X, padx=4, pady=1)
        ttk.Label(row3, text='备注:').pack(side=tk.LEFT)
        self._note_var = tk.StringVar(value='')
        ttk.Entry(row3, textvariable=self._note_var, width=20).pack(side=tk.LEFT, padx=4)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        # -- Profile section --
        profile_frame = ttk.LabelFrame(self, text='测试方案')
        profile_frame.pack(fill=tk.X, padx=4, pady=2)

        pf_row = ttk.Frame(profile_frame)
        pf_row.pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(pf_row, text='方案:').pack(side=tk.LEFT)
        self._profile_var = tk.StringVar(value='')
        self._profile_combo = ttk.Combobox(
            pf_row, textvariable=self._profile_var, width=16, state='readonly',
        )
        self._profile_combo.pack(side=tk.LEFT, padx=4)
        self._profile_load_btn = ttk.Button(
            pf_row, text='加载', width=4, command=self._on_profile_load,
        )
        self._profile_load_btn.pack(side=tk.LEFT, padx=2)

        self._profile_info_var = tk.StringVar(value='')
        ttk.Label(
            profile_frame, textvariable=self._profile_info_var,
            font=(cjk_family(), 8), foreground='gray', wraplength=200,
        ).pack(fill=tk.X, padx=4, pady=(0, 4))

        self._refresh_profiles()

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        # -- Excel --
        excel_frame = ttk.Frame(self)
        excel_frame.pack(fill=tk.X, padx=8, pady=2)
        self._excel_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(excel_frame, text='写入Excel', variable=self._excel_var,
                         command=self._on_excel_toggle).pack(side=tk.LEFT)
        self._excel_path_var = tk.StringVar(value='')
        ttk.Entry(excel_frame, textvariable=self._excel_path_var, width=18).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        ttk.Button(excel_frame, text='...', width=3, command=self._on_browse_excel).pack(side=tk.LEFT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        # -- Auto-test --
        at_frame = ttk.LabelFrame(self, text='自动测试')
        at_frame.pack(fill=tk.X, padx=4, pady=2)

        at_btn_frame = ttk.Frame(at_frame)
        at_btn_frame.pack(fill=tk.X, padx=4, pady=2)
        self._autotest_start_btn = ttk.Button(
            at_btn_frame, text='开始', command=self._on_autotest_start, width=6
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
        ttk.Label(at_frame, textvariable=self._autotest_progress_var,
                  font=(cjk_family(), 9)).pack(fill=tk.X, padx=4, pady=2)

        self._autotest_case_var = tk.StringVar(value='')
        ttk.Label(at_frame, textvariable=self._autotest_case_var,
                  font=(cjk_family(), 9), foreground='#0066CC', wraplength=200
                  ).pack(fill=tk.X, padx=4, pady=(0, 4))

        # -- Error label --
        self._error_label = ttk.Label(
            self, text='', foreground='red', wraplength=200, font=(cjk_family(), 9)
        )
        self._error_label.pack(fill=tk.X, padx=8, pady=4)

    # -- public state methods ------------------------------------------------

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        self._update_button_states()

    def set_continuous_running(self, running: bool) -> None:
        self._continuous_running = running
        self._continuous_btn.config(
            text='停止连续' if running else '连续测量'
        )
        self._update_button_states()

    def show_error(self, message: str) -> None:
        self._error_label.config(text=message)
        if self._error_after_id:
            self.after_cancel(self._error_after_id)
        self._error_after_id = self.after(5000, lambda: self._error_label.config(text=''))

    # -- getter methods -------------------------------------------------------

    def get_mode(self) -> MeasurementMode:
        return MeasurementMode(self._mode_var.get())

    def get_image_mode(self) -> str:
        return self._image_mode_var.get()

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

    def get_note(self) -> str:
        return self._note_var.get()

    def is_excel_write_enabled(self) -> bool:
        return self._excel_var.get()

    def get_excel_path(self) -> str:
        return self._excel_path_var.get()

    def get_interval(self) -> float:
        try:
            val = float(self._interval_var.get())
            return max(0.1, val)
        except ValueError:
            return 1.0

    def set_test_case_fields(self, case) -> None:
        self._image_mode_var.set(case.image_mode)
        self._peak_brightness_var.set(case.peak_brightness)
        self._backlight_var.set(f'{case.backlight_value:.0f}')
        self._local_dimming_var.set(case.local_dimming)
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

    # -- callbacks (to be set by MainWindow) ----------------------------------

    _autotest_start_callback = None
    _autotest_pause_callback = None
    _autotest_stop_callback = None
    _profile_load_callback = None

    def set_autotest_start_callback(self, callback) -> None:
        self._autotest_start_callback = callback

    def set_autotest_pause_callback(self, callback) -> None:
        self._autotest_pause_callback = callback

    def set_autotest_stop_callback(self, callback) -> None:
        self._autotest_stop_callback = callback

    def set_profile_load_callback(self, callback) -> None:
        self._profile_load_callback = callback

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

    # -- Profile --------------------------------------------------------------

    def _refresh_profiles(self) -> None:
        paths = list_profiles()
        names = [p.stem for p in paths]
        self._profile_combo['values'] = names
        self._profile_paths = {p.stem: str(p) for p in paths}
        if names:
            self._profile_var.set(names[0])
            self._profile_info_var.set(f'共 {len(names)} 个方案可用')
        else:
            self._profile_info_var.set('未找到方案文件 (profiles/*.json)')

    def _on_profile_load(self) -> None:
        name = self._profile_var.get()
        if not name:
            self.show_error('请选择一个测试方案')
            return
        if name not in self._profile_paths:
            self.show_error(f'方案文件不存在: {name}')
            return
        try:
            profile = load_profile(self._profile_paths[name])
        except Exception as e:
            self.show_error(f'加载方案失败: {e}')
            return
        self._profile_info_var.set(f'{profile.name}: {len(profile.steps)} 步')
        if self._profile_load_callback:
            self._profile_load_callback(profile)

    # -- internal ------------------------------------------------------------

    def _update_button_states(self) -> None:
        self._measure_btn.config(
            state='normal' if self._connected and not self._continuous_running else 'disabled'
        )
        self._continuous_btn.config(
            state='normal' if self._connected else 'disabled'
        )
        self._zero_cal_btn.config(
            state='normal' if self._connected and not self._continuous_running else 'disabled'
        )

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

    def _on_autotest_start(self) -> None:
        if self._autotest_start_callback:
            self._autotest_start_callback()

    def _on_autotest_pause(self) -> None:
        if self._autotest_pause_callback:
            self._autotest_pause_callback()

    def _on_autotest_stop(self) -> None:
        if self._autotest_stop_callback:
            self._autotest_stop_callback()
