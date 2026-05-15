import queue
import tkinter as tk
from tkinter import ttk

from ui.fonts import init as init_fonts, cjk_family
from ui.main_window import MainWindow
from util.config import AppConfig
from worker.measurement_worker import MeasurementWorker


class Application:
    def __init__(self):
        self._root = tk.Tk()
        init_fonts(self._root)
        self._configure_theme()
        self._config = AppConfig.load()
        self._result_queue = queue.Queue()
        self._worker = MeasurementWorker(self._result_queue)
        self._main_window = MainWindow(
            self._root, self._worker, self._result_queue, self._config
        )

    def _configure_theme(self) -> None:
        """Set ttk theme fonts to support CJK characters on all platforms."""
        style = ttk.Style()
        family = cjk_family()
        for widget_type in ('TLabel', 'TButton', 'TLabelframe.Label',
                            'TCheckbutton', 'TRadiobutton', 'TEntry',
                            'TCombobox'):
            try:
                style.configure(widget_type, font=(family, 10))
            except Exception:
                pass
        style.configure('Treeview', font=(family, 9))
        style.configure('Treeview.Heading', font=(family, 9, 'bold'))

    def run(self) -> None:
        self._root.mainloop()
