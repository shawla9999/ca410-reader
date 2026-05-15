import logging
import queue
import threading

from driver.ca410_driver import CA410Driver
from driver.ca410_types import MeasurementMode
from driver.errors import CA410Error, ConnectionError

logger = logging.getLogger(__name__)

RESULT_SINGLE = 'single'
RESULT_CONTINUOUS = 'continuous'
RESULT_ERROR = 'error'
STATUS_CONNECTED = 'connected'
STATUS_DISCONNECTED = 'disconnected'
STATUS_CALIBRATING = 'calibrating'
STATUS_CALIBRATED = 'calibrated'


class MeasurementWorker:
    """Background measurement thread manager.

    All driver calls run on worker threads. Results are pushed to a
    queue consumed by the UI via tkinter.after() polling.
    """

    def __init__(self, result_queue: queue.Queue):
        self._result_queue = result_queue
        self._driver = CA410Driver()
        self._stop_event = threading.Event()
        self._continuous_thread: threading.Thread | None = None

    def connect(self, port: str | None = None) -> None:
        t = threading.Thread(target=self._run_connect, args=(port,), daemon=True)
        t.start()

    def disconnect(self) -> None:
        self.stop_continuous()
        try:
            self._driver.disconnect()
        except Exception as e:
            logger.warning('Disconnect error: %s', e)
        self._result_queue.put((STATUS_DISCONNECTED, None))

    def measure_single(self, mode: MeasurementMode | None = None) -> None:
        t = threading.Thread(target=self._run_single, args=(mode,), daemon=True)
        t.start()

    def start_continuous(self, interval: float = 1.0, mode: MeasurementMode | None = None) -> None:
        if self._continuous_thread and self._continuous_thread.is_alive():
            return
        self._stop_event.clear()
        self._continuous_thread = threading.Thread(
            target=self._run_continuous, args=(interval, mode), daemon=True
        )
        self._continuous_thread.start()

    def stop_continuous(self) -> None:
        self._stop_event.set()
        if self._continuous_thread and self._continuous_thread.is_alive():
            self._continuous_thread.join(timeout=3.0)
        self._continuous_thread = None

    def zero_calibrate(self) -> None:
        self._result_queue.put((STATUS_CALIBRATING, None))
        t = threading.Thread(target=self._run_calibrate, daemon=True)
        t.start()

    def set_mode(self, mode: MeasurementMode) -> None:
        t = threading.Thread(target=self._run_set_mode, args=(mode,), daemon=True)
        t.start()

    @property
    def is_continuous_running(self) -> bool:
        return self._continuous_thread is not None and self._continuous_thread.is_alive()

    def _run_connect(self, port: str | None) -> None:
        try:
            self._driver.connect(port)
            self._result_queue.put((STATUS_CONNECTED, port))
        except CA410Error as e:
            self._result_queue.put((RESULT_ERROR, str(e)))
        except Exception as e:
            self._result_queue.put((RESULT_ERROR, f'连接失败: {e}'))

    def _run_single(self, mode: MeasurementMode | None = None) -> None:
        try:
            if not self._driver.is_connected:
                self._result_queue.put((RESULT_ERROR, 'CA-410 未连接，请先连接设备'))
                return
            logger.info('Single measure: mode=%s, connected=%s', mode, self._driver.is_connected)
            if mode is not None:
                try:
                    self._driver.set_mode(mode)
                except CA410Error as e:
                    logger.warning('set_mode failed: %s, continuing with current mode', e)
            result = self._driver.measure()
            logger.info('Single measure result: lv=%.2f', result.lv)
            self._result_queue.put((RESULT_SINGLE, result))
        except CA410Error as e:
            logger.warning('Single measure CA410Error: %s', e)
            self._result_queue.put((RESULT_ERROR, str(e)))
        except Exception as e:
            logger.error('Single measure exception: %s', e, exc_info=True)
            self._result_queue.put((RESULT_ERROR, f'测量失败: {e}'))

    def _run_continuous(self, interval: float, mode: MeasurementMode | None = None) -> None:
        try:
            if mode is not None:
                self._driver.set_mode(mode)
        except CA410Error as e:
            self._result_queue.put((RESULT_ERROR, str(e)))
            return
        except Exception as e:
            self._result_queue.put((RESULT_ERROR, f'设置模式失败: {e}'))
            return

        while not self._stop_event.is_set():
            try:
                result = self._driver.measure()
                self._result_queue.put((RESULT_CONTINUOUS, result))
            except CA410Error as e:
                self._result_queue.put((RESULT_ERROR, str(e)))
                if isinstance(e, ConnectionError):
                    self._stop_event.set()
                    self._result_queue.put((STATUS_DISCONNECTED, None))
                    return
            except Exception as e:
                self._result_queue.put((RESULT_ERROR, f'连续测量错误: {e}'))
                self._stop_event.set()
                return
            self._stop_event.wait(timeout=interval)

    def _run_calibrate(self) -> None:
        try:
            self._driver.zero_calibrate()
            self._result_queue.put((STATUS_CALIBRATED, None))
        except CA410Error as e:
            self._result_queue.put((RESULT_ERROR, str(e)))
        except Exception as e:
            self._result_queue.put((RESULT_ERROR, f'零点校准失败: {e}'))

    def _run_set_mode(self, mode: MeasurementMode) -> None:
        try:
            self._driver.set_mode(mode)
        except CA410Error as e:
            self._result_queue.put((RESULT_ERROR, str(e)))
        except Exception as e:
            self._result_queue.put((RESULT_ERROR, f'切换模式失败: {e}'))
