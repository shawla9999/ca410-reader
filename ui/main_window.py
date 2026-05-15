import logging
import queue
import threading

import tkinter as tk
from tkinter import ttk, messagebox

logger = logging.getLogger(__name__)

from driver.ca410_types import ConnectionStatus, MeasurementMode, MODE_LABELS, XyLvResult, TduvLvResult
from driver.murideo_driver import (
    MurideoDriver, MurideoError, MurideoConnectionError,
    CAT_HDR, CAT_PATTERN, PATTERN_WINDOW,
    HDR_OFF, HDR_HDR10,
)
from worker import measurement_worker as mw
from worker.auto_test_worker import AutoTestWorker, AUTO_TEST_STARTED, AUTO_TEST_PROGRESS, AUTO_TEST_CASE_DONE, AUTO_TEST_ALL_DONE, AUTO_TEST_ERROR, AUTO_TEST_STOPPED
from ui.connection_panel import ConnectionPanel
from ui.measurement_panel import MeasurementPanel
from ui.control_panel import ControlPanel
from ui.history_panel import HistoryPanel
from util.excel_exporter import export_to_excel
from util.test_case_loader import load_test_cases
from util.config import AppConfig

MURIDEO_CONNECTED = 'murideo_connected'
MURIDEO_DISCONNECTED = 'murideo_disconnected'
MURIDEO_SET_RESULT = 'murideo_set_result'
MURIDEO_ERROR = 'murideo_error'


class MainWindow:
    """Top-level application window."""

    WINDOW_TITLE = 'CA-410 色彩分析仪读取器'
    QUEUE_POLL_MS = 100

    def __init__(self, root: tk.Tk, worker: mw.MeasurementWorker,
                 result_queue: queue.Queue, config: AppConfig):
        self._root = root
        self._worker = worker
        self._queue = result_queue
        self._config = config
        self._connection_status = ConnectionStatus.DISCONNECTED
        self._excel_write_count = 0
        self._murideo = MurideoDriver()
        self._auto_test = AutoTestWorker(result_queue, self._murideo)
        self._auto_testing = False
        self._manual_cases: list = []
        self._manual_case_index = 0

        self._setup_window()
        self._create_widgets()
        self._restore_config()
        self._poll_queue()

    def _setup_window(self):
        self._root.title(self.WINDOW_TITLE)
        self._root.minsize(950, 650)
        self._root.protocol('WM_DELETE_WINDOW', self._on_close)

    def _create_widgets(self):
        # Row 0: Connection panel
        self._conn_panel = ConnectionPanel(self._root, self._worker)
        self._conn_panel.grid(row=0, column=0, columnspan=2, sticky='ew', padx=5, pady=5)

        # Row 1: Measurement panel (left) + Control panel (right)
        self._meas_panel = MeasurementPanel(self._root)
        self._meas_panel.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)

        self._ctrl_panel = ControlPanel(self._root, self._worker)
        self._ctrl_panel.grid(row=1, column=1, sticky='ns', padx=5, pady=5)

        # Row 2: History panel
        self._history_panel = HistoryPanel(self._root)
        self._history_panel.grid(row=2, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)

        # Grid weights
        self._root.columnconfigure(0, weight=3)
        self._root.columnconfigure(1, weight=1)
        self._root.rowconfigure(1, weight=2)
        self._root.rowconfigure(2, weight=1)

        # Wire Murideo callbacks
        self._ctrl_panel.set_murideo_connect_callback(self._on_murideo_connect)
        self._ctrl_panel.set_murideo_disconnect_callback(self._on_murideo_disconnect)
        self._ctrl_panel.set_murideo_set_callback(self._on_murideo_set)

        # Wire auto-test callbacks
        self._ctrl_panel.set_autotest_start_callback(self._on_autotest_start)
        self._ctrl_panel.set_autotest_pause_callback(self._on_autotest_pause)
        self._ctrl_panel.set_autotest_stop_callback(self._on_autotest_stop)

        # Wire auto-test measure callback
        self._auto_test.set_measure_callback(self._on_autotest_measure)

    def _restore_config(self):
        if self._config.mode == 'TduvLv':
            self._ctrl_panel._mode_var.set(MeasurementMode.TDUV_LV)
            self._meas_panel.set_mode(MeasurementMode.TDUV_LV)
        self._ctrl_panel._interval_var.set(str(self._config.continuous_interval))
        if self._config.window_geometry:
            self._root.geometry(self._config.window_geometry)
        if self._config.murideo_host:
            self._ctrl_panel.set_murideo_host(self._config.murideo_host)

    def _poll_queue(self):
        while True:
            try:
                msg_type, data = self._queue.get_nowait()
            except queue.Empty:
                break
            logger.debug('Queue event: type=%s', msg_type)
            self._handle_result(msg_type, data)
        self._root.after(self.QUEUE_POLL_MS, self._poll_queue)

    def _attach_user_inputs(self, result) -> None:
        """Attach user-input metadata to result."""
        result.image_mode = self._ctrl_panel.get_image_mode()
        result.window_ratio = self._ctrl_panel.get_window_ratio()
        result.window_brightness = self._ctrl_panel.get_window_brightness()
        result.peak_brightness = self._ctrl_panel.get_peak_brightness()
        result.backlight_value = self._ctrl_panel.get_backlight_value()
        result.local_dimming = self._ctrl_panel.get_local_dimming()
        result.hdr_sdr = self._ctrl_panel.get_hdr_sdr()
        result.note = self._ctrl_panel.get_note()

    def _result_to_excel_record(self, result) -> dict:
        """Convert a measurement result to a dict matching Excel headers."""
        if isinstance(result, TduvLvResult):
            x_val = ''
            y_val = ''
        else:
            x_val = f'{result.x:.4f}'
            y_val = f'{result.y:.4f}'

        return {
            '编号': '',
            '图像模式': result.image_mode or '',
            '峰值亮度': result.peak_brightness or '',
            '当前背光值': f'{result.backlight_value:.0f}' if result.backlight_value is not None else '',
            'Local Dimming': result.local_dimming or '',
            '小窗口大小': f'{result.window_ratio:.0f}%' if result.window_ratio is not None else '',
            'HDR/SDR': result.hdr_sdr or '',
            '白块亮度(nit)': f'{result.window_brightness:.0f}' if result.window_brightness is not None else '',
            'Lv (cd/m²)': f'{result.lv:.2f}',
            'x': x_val,
            'y': y_val,
            '备注': result.note or '',
        }

    def _auto_write_excel(self, result) -> None:
        """Write measurement to Excel if the checkbox is enabled."""
        if not self._ctrl_panel.is_excel_write_enabled():
            return
        filepath = self._ctrl_panel.get_excel_path()
        if not filepath:
            self._ctrl_panel.show_error('请选择Excel文件路径')
            return
        try:
            record = self._result_to_excel_record(result)
            matched, unmatched = export_to_excel([record], filepath)
            self._excel_write_count += 1
            if matched > 0:
                self._ctrl_panel.show_error(f'已写入测试用例 (共{self._excel_write_count}条)')
            else:
                self._ctrl_panel.show_error(f'未匹配，写入额外数据 (共{self._excel_write_count}条)')
        except FileNotFoundError:
            self._ctrl_panel.show_error('Excel文件不存在，请重新选择')
        except Exception as e:
            logger.error('Excel write error: %s', e)
            self._ctrl_panel.show_error(f'写入Excel失败: {e}')

    def _handle_result(self, msg_type: str, data) -> None:
        if msg_type in (mw.RESULT_SINGLE, mw.RESULT_CONTINUOUS):
            # Auto-set Murideo before measurement (manual mode)
            if self._ctrl_panel.is_murideo_auto_set() and self._murideo.is_connected and not self._auto_testing:
                self._auto_set_murideo()
            self._attach_user_inputs(data)
            self._meas_panel.update_values(data)
            self._history_panel.add_entry(data)
            self._auto_write_excel(data)

            # If auto-testing, advance to next case after measurement
            if self._auto_testing and self._auto_test.is_running:
                self._auto_test.advance()

        elif msg_type == mw.RESULT_ERROR:
            self._ctrl_panel.show_error(str(data))
            if self._connection_status == ConnectionStatus.CONNECTING:
                self._update_connection_status(ConnectionStatus.ERROR)

        elif msg_type == mw.STATUS_CONNECTED:
            self._update_connection_status(ConnectionStatus.CONNECTED)
            mode = self._ctrl_panel.get_mode()
            self._meas_panel.set_mode(mode)
            self._config.last_port = data

        elif msg_type == mw.STATUS_DISCONNECTED:
            self._update_connection_status(ConnectionStatus.DISCONNECTED)
            if self._ctrl_panel._continuous_running:
                self._ctrl_panel.set_continuous_running(False)

        elif msg_type == mw.STATUS_CALIBRATING:
            self._ctrl_panel.show_error('正在零点校准...')

        elif msg_type == mw.STATUS_CALIBRATED:
            self._ctrl_panel.show_error('零点校准完成')

        # -- Murideo events --
        elif msg_type == MURIDEO_CONNECTED:
            self._ctrl_panel.set_murideo_connected(True)
            self._ctrl_panel.show_error(f'Murideo 已连接 ({data})')

        elif msg_type == MURIDEO_DISCONNECTED:
            self._ctrl_panel.set_murideo_connected(False)

        elif msg_type == MURIDEO_SET_RESULT:
            self._ctrl_panel.show_error(data)

        elif msg_type == MURIDEO_ERROR:
            self._ctrl_panel.show_error(str(data))

        # -- Auto-test events --
        elif msg_type == AUTO_TEST_STARTED:
            self._auto_testing = True
            self._ctrl_panel.set_autotest_state(running=True)

        elif msg_type == AUTO_TEST_PROGRESS:
            index = data['index']
            total = data['total']
            case = data['case']
            # Update UI fields from test case
            self._ctrl_panel.set_test_case_fields(case)
            self._ctrl_panel.set_autotest_progress(index, total, case)
            # Auto-enable Excel write
            if not self._ctrl_panel.is_excel_write_enabled():
                self._ctrl_panel._excel_var.set(True)

        elif msg_type == AUTO_TEST_ALL_DONE:
            self._auto_testing = False
            self._ctrl_panel.set_autotest_state(running=False)
            self._ctrl_panel.show_error(f'自动测试完成! 共 {data["total"]} 条')

        elif msg_type == AUTO_TEST_STOPPED:
            self._auto_testing = False
            self._ctrl_panel.set_autotest_state(running=False)

        elif msg_type == AUTO_TEST_ERROR:
            self._ctrl_panel.show_error(str(data))

    def _update_connection_status(self, status: ConnectionStatus) -> None:
        self._connection_status = status
        self._conn_panel.update_status(status)
        self._ctrl_panel.set_connected(status == ConnectionStatus.CONNECTED)

    # -- Murideo operations ---------------------------------------------------

    def _on_murideo_connect(self) -> None:
        host = self._ctrl_panel.get_murideo_host()
        t = threading.Thread(target=self._run_murideo_connect, args=(host,), daemon=True)
        t.start()

    def _on_murideo_disconnect(self) -> None:
        try:
            self._murideo.disconnect()
        except Exception:
            pass
        self._queue.put((MURIDEO_DISCONNECTED, None))

    def _on_murideo_set(self) -> None:
        if not self._murideo.is_connected:
            self._ctrl_panel.show_error('Murideo 未连接')
            return
        if self._ctrl_panel.is_murideo_auto_set():
            # Auto mode: lookup test case and display in UI
            case = self._get_current_test_case()
            if case is None:
                self._ctrl_panel.show_error('未找到测试用例，请先选择Excel文件')
                return
            self._ctrl_panel.set_test_case_fields(case)
            self._manual_case_index += 1
            hdr_sdr = case.hdr_sdr
            window_size = case.window_size
            brightness = case.window_brightness
        else:
            # Manual mode: validate UI fields
            window_size = self._ctrl_panel.get_window_ratio()
            hdr_sdr = self._ctrl_panel.get_hdr_sdr()
            brightness = self._ctrl_panel.get_window_brightness()
            logger.info('Manual Murideo set: window_size=%s, hdr_sdr=%s, brightness=%s',
                        window_size, hdr_sdr, brightness)
            errors = []
            if window_size is None:
                errors.append('小窗口大小')
            if not hdr_sdr:
                errors.append('HDR/SDR')
            if brightness is None:
                errors.append('IRE Level')
            if errors:
                self._ctrl_panel.show_error(f'请填写: {", ".join(errors)}')
                return
        t = threading.Thread(
            target=self._run_murideo_set,
            args=(hdr_sdr, window_size, brightness),
            daemon=True,
        )
        t.start()

    def _get_current_test_case(self):
        """Get the current test case for manual mode."""
        if self._auto_testing and self._auto_test.current_case:
            return self._auto_test.current_case
        if not self._manual_cases:
            filepath = self._ctrl_panel.get_excel_path()
            if filepath:
                try:
                    self._manual_cases = load_test_cases(filepath)
                    self._manual_case_index = 0
                except Exception:
                    return None
        if self._manual_cases and self._manual_case_index < len(self._manual_cases):
            return self._manual_cases[self._manual_case_index]
        return None

    def _run_murideo_connect(self, host: str) -> None:
        try:
            self._murideo.connect(host)
            self._queue.put((MURIDEO_CONNECTED, host))
        except MurideoError as e:
            self._queue.put((MURIDEO_ERROR, str(e)))
        except Exception as e:
            self._queue.put((MURIDEO_ERROR, f'Murideo 连接失败: {e}'))

    def _run_murideo_set(self, hdr_sdr: str, window_size: float | None,
                         brightness: float | None) -> None:
        try:
            parts = []
            hdr_map = {'HDR': HDR_HDR10, 'SDR': HDR_OFF}
            hdr_mode = hdr_map.get(hdr_sdr)
            ire = int(brightness) if brightness is not None else 255
            # Set IRE window + HDR in one connection
            if window_size is not None:
                try:
                    self._murideo.set_ire_window(
                        ire=ire, window_size=int(window_size),
                        hdr_mode=hdr_mode,
                    )
                    if hdr_mode is not None:
                        parts.append(f'HDR={hdr_sdr}')
                    parts.append(f'窗口{window_size:.0f}%')
                    parts.append(f'IRE={ire}')
                except MurideoError as e:
                    parts.append(f'IRE/窗口: {e}')
            else:
                if hdr_mode is not None:
                    try:
                        self._murideo.set_hdr(hdr_mode)
                        parts.append(f'HDR={hdr_sdr}')
                    except MurideoError as e:
                        parts.append(f'HDR: {e}')
                try:
                    self._murideo.set_pattern(PATTERN_WINDOW)
                    parts.append('Window图案')
                except MurideoError as e:
                    parts.append(f'图案: {e}')
            if brightness is not None:
                parts.append(f'IRE={brightness:.0f}')
            msg = 'Murideo: ' + ', '.join(parts) if parts else '无操作'
            self._queue.put((MURIDEO_SET_RESULT, msg))
        except Exception as e:
            self._queue.put((MURIDEO_ERROR, f'Murideo 设置失败: {e}'))

    def _auto_set_murideo(self) -> None:
        """Auto-set Murideo before manual measurement (non-blocking)."""
        hdr_sdr = self._ctrl_panel.get_hdr_sdr()
        if self._ctrl_panel.is_murideo_auto_set():
            case = self._get_current_test_case()
            if case:
                self._ctrl_panel.set_test_case_fields(case)
                hdr_sdr = case.hdr_sdr
                self._manual_case_index += 1
        hdr_map = {'HDR': HDR_HDR10, 'SDR': HDR_OFF}
        hdr_mode = hdr_map.get(hdr_sdr)
        window_size = self._ctrl_panel.get_window_ratio()
        brightness = self._ctrl_panel.get_window_brightness()
        t = threading.Thread(
            target=self._run_murideo_auto_set,
            args=(hdr_mode, window_size, brightness),
            daemon=True,
        )
        t.start()

    def _run_murideo_auto_set(self, hdr_mode: int | None,
                              window_size: float | None = None,
                              brightness: float | None = None) -> None:
        try:
            ire = int(brightness) if brightness is not None else 255
            if window_size is not None:
                self._murideo.set_ire_window(ire, int(window_size), hdr_mode=hdr_mode)
            else:
                if hdr_mode is not None:
                    self._murideo.set_hdr(hdr_mode)
                self._murideo.set_pattern(PATTERN_WINDOW)
        except Exception as e:
            logger.warning('Auto-set Murideo failed: %s', e)

    # -- Auto-test operations --------------------------------------------------

    def _on_autotest_start(self) -> None:
        filepath = self._ctrl_panel.get_excel_path()
        if not filepath:
            self._ctrl_panel.show_error('请先选择测试用例Excel文件')
            return

        try:
            cases = load_test_cases(filepath)
        except Exception as e:
            self._ctrl_panel.show_error(f'读取测试用例失败: {e}')
            return

        if not cases:
            self._ctrl_panel.show_error('Excel中没有测试用例')
            return

        self._auto_test.configure(cases, filepath)
        self._auto_test.start()
        self._ctrl_panel.show_error(f'自动测试开始: {len(cases)} 条用例')

    def _on_autotest_pause(self) -> None:
        if self._auto_test.is_paused:
            self._auto_test.resume()
            self._ctrl_panel.set_autotest_state(running=True, paused=False)
            # Resume also triggers the next measurement
            self._auto_test.advance()
        else:
            self._auto_test.pause()
            self._ctrl_panel.set_autotest_state(running=True, paused=True)
            self._ctrl_panel.show_error('自动测试已暂停')

    def _on_autotest_stop(self) -> None:
        self._auto_test.stop()
        self._auto_testing = False
        self._ctrl_panel.set_autotest_state(running=False)
        self._ctrl_panel.show_error('自动测试已停止')

    def _on_autotest_measure(self) -> None:
        """Called by AutoTestWorker to trigger a CA-410 measurement."""
        self._worker.measure_single(mode=self._ctrl_panel.get_mode())

    # -- window close ----------------------------------------------------------

    def _on_close(self):
        self._auto_test.stop()
        self._worker.stop_continuous()
        self._worker.disconnect()
        if self._murideo.is_connected:
            try:
                self._murideo.disconnect()
            except Exception:
                pass
        self._config.mode = MODE_LABELS.get(
            self._ctrl_panel.get_mode(), 'xyLv'
        )
        self._config.continuous_interval = self._ctrl_panel.get_interval()
        self._config.murideo_host = self._ctrl_panel.get_murideo_host()
        try:
            self._config.window_geometry = self._root.geometry()
        except Exception:
            pass
        self._config.save()
        self._root.destroy()
