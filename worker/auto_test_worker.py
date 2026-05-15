"""Auto-test worker: iterate through test cases automatically.

Workflow for each test case:
1. Set Murideo parameters (HDR/SDR, window pattern)
2. Wait for user to adjust TV settings (or auto-set UI fields)
3. Trigger CA-410 measurement
4. Write result to Excel
5. Move to next test case
"""

import logging
import queue
import threading
import time

from driver.murideo_driver import (
    MurideoDriver, MurideoError,
    CAT_HDR, CAT_PATTERN, CAT_COLOR_DEPTH, CAT_BT2020,
    PATTERN_WINDOW, HDR_OFF, HDR_HDR10,
)
from util.test_case_loader import TestCase
from util.excel_exporter import export_to_excel
from util.profile import TestProfile

logger = logging.getLogger(__name__)

# Queue message types
AUTO_TEST_STARTED = 'auto_test_started'
AUTO_TEST_PROGRESS = 'auto_test_progress'
AUTO_TEST_CASE_DONE = 'auto_test_case_done'
AUTO_TEST_ALL_DONE = 'auto_test_all_done'
AUTO_TEST_ERROR = 'auto_test_error'
AUTO_TEST_PAUSED = 'auto_test_paused'
AUTO_TEST_STOPPED = 'auto_test_stopped'


def profile_to_test_cases(profile: TestProfile) -> list[TestCase]:
    """Convert a TestProfile's steps into TestCase objects.

    Each step inherits defaults from the profile for missing fields.
    """
    cases = []
    for i, step in enumerate(profile.steps):
        resolved = step.resolved(profile.defaults)
        hdr_sdr = 'HDR' if resolved.get('hdr', 0) != 0 else 'SDR'
        cases.append(TestCase(
            row=0,
            test_id=f'P{i + 1:03d}',
            image_mode='',
            peak_brightness='',
            backlight_value=0,
            local_dimming='',
            window_size=resolved.get('window_size', 100),
            hdr_sdr=hdr_sdr,
            window_brightness=resolved.get('ire', 255),
            note=step.note,
            timing=resolved.get('timing'),
            color_space=resolved.get('color_space'),
            color_depth=resolved.get('color_depth'),
            pattern=resolved.get('pattern'),
        ))
    return cases


class AutoTestWorker:
    """Manages automatic test case execution.

    Runs in a background thread. Communicates with the UI via a queue.
    The UI polls the queue and updates accordingly.
    """

    def __init__(self, result_queue: queue.Queue, murideo: MurideoDriver):
        self._queue = result_queue
        self._murideo = murideo
        self._cases: list[TestCase] = []
        self._current_index = 0
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._paused = True  # Start paused so UI can trigger first measurement
        self._running = False
        self._thread: threading.Thread | None = None
        self._measure_callback = None  # Set by MainWindow
        self._excel_path = ''
        self._profile: TestProfile | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def total_cases(self) -> int:
        return len(self._cases)

    @property
    def current_case(self) -> TestCase | None:
        if 0 <= self._current_index < len(self._cases):
            return self._cases[self._current_index]
        return None

    def configure(self, cases: list[TestCase], excel_path: str,
                  start_index: int = 0,
                  profile: TestProfile | None = None) -> None:
        self._cases = cases
        self._excel_path = excel_path
        self._current_index = start_index
        self._profile = profile

    def set_measure_callback(self, callback) -> None:
        """Set callback to trigger CA-410 measurement from the worker thread."""
        self._measure_callback = callback

    def start(self) -> None:
        if self._running:
            return
        if not self._cases:
            self._queue.put((AUTO_TEST_ERROR, '没有测试用例'))
            return
        self._stop_event.clear()
        self._pause_event.clear()
        self._paused = False
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        self._paused = True
        self._pause_event.set()

    def resume(self) -> None:
        self._paused = False
        self._pause_event.clear()

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.clear()  # Unblock if paused
        self._running = False
        self._paused = False

    def advance(self) -> None:
        """Signal that the current measurement is done and we should advance.

        Called from the UI after a CA-410 measurement result is received.
        """
        self._pause_event.set()  # Break the pause wait

    def _run(self) -> None:
        """Main auto-test loop."""
        self._queue.put((AUTO_TEST_STARTED, {
            'total': len(self._cases),
            'start_index': self._current_index,
        }))

        while self._current_index < len(self._cases):
            if self._stop_event.is_set():
                self._queue.put((AUTO_TEST_STOPPED, None))
                self._running = False
                return

            case = self._cases[self._current_index]

            # Step 1: Set Murideo parameters
            self._set_murideo(case)

            # Step 2: Notify UI with current case info
            self._queue.put((AUTO_TEST_PROGRESS, {
                'index': self._current_index,
                'total': len(self._cases),
                'case': case,
            }))

            # Step 3: Trigger CA-410 measurement
            if self._measure_callback:
                self._measure_callback()
            else:
                logger.error('No measure callback set')

            # Step 4: Wait for measurement to complete
            # The UI will call advance() when measurement result arrives
            self._pause_event.wait()
            self._pause_event.clear()

            if self._stop_event.is_set():
                self._queue.put((AUTO_TEST_STOPPED, None))
                self._running = False
                return

            # Step 5: Move to next case
            self._current_index += 1

        self._running = False
        self._queue.put((AUTO_TEST_ALL_DONE, {
            'total': len(self._cases),
        }))

    def _set_murideo(self, case: TestCase) -> None:
        """Set Murideo parameters for a test case.

        Uses extended TestCase fields (timing, color_space, pattern) when
        available; falls back to legacy hdr_sdr-based logic otherwise.
        """
        if not self._murideo.is_connected:
            logger.warning('Murideo not connected, skipping device setup')
            return

        try:
            # Determine HDR mode: prefer explicit field, else derive from hdr_sdr
            if case.hdr_sdr == 'HDR' or case.hdr_sdr == 'HLG':
                hdr_mode = HDR_HDR10
            else:
                hdr_mode = HDR_OFF

            bt2020 = 1 if case.hdr_sdr == 'HDR' else 0
            ire = int(case.window_brightness) if case.window_brightness else 255

            # Use extended fields if set, otherwise sensible defaults
            timing = case.timing
            color_space = case.color_space
            color_depth = case.color_depth if case.color_depth is not None else 1
            pattern_id = case.pattern

            self._murideo.set_ire_window(
                ire=ire, window_size=int(case.window_size),
                hdr_mode=hdr_mode, bt2020=bt2020, color_depth=color_depth,
                timing=timing, color_space=color_space, pattern_id=pattern_id,
            )

            logger.info('Murideo set: HDR/SDR=%s, 窗口%d%%, IRE=%d, timing=%s, cs=%s, pat=%s',
                        case.hdr_sdr, int(case.window_size), ire,
                        timing, color_space, pattern_id)
        except MurideoError as e:
            logger.error('Failed to set Murideo: %s', e)
            self._queue.put((AUTO_TEST_ERROR, f'Murideo 设置失败: {e}'))
