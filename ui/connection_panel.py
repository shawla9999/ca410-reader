import tkinter as tk
from tkinter import ttk

import serial.tools.list_ports

from driver.ca410_types import ConnectionStatus
from ui.fonts import cjk_family
from worker import measurement_worker as mw


class ConnectionPanel(ttk.Frame):
    """COM port selection and connection status indicator."""

    def __init__(self, parent, worker: mw.MeasurementWorker, **kwargs):
        super().__init__(parent, **kwargs)
        self._worker = worker
        self._status = ConnectionStatus.DISCONNECTED
        self._create_widgets()

    def _create_widgets(self):
        ttk.Label(self, text='端口:').pack(side=tk.LEFT, padx=(5, 2))
        self._port_var = tk.StringVar()
        self._port_combo = ttk.Combobox(
            self, textvariable=self._port_var, width=20, state='readonly'
        )
        self._port_combo.pack(side=tk.LEFT, padx=2)
        self.refresh_ports()

        ttk.Button(self, text='刷新', command=self.refresh_ports, width=5).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(self, text='连接', command=self._on_connect, width=6).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(self, text='断开', command=self._on_disconnect, width=6).pack(
            side=tk.LEFT, padx=2
        )

        self._status_canvas = tk.Canvas(self, width=16, height=16, highlightthickness=0)
        self._status_canvas.pack(side=tk.LEFT, padx=(15, 2))
        self._status_label = ttk.Label(self, text='未连接', font=(cjk_family(), 10))
        self._status_label.pack(side=tk.LEFT, padx=2)
        self._draw_status()

    def refresh_ports(self) -> None:
        ports = serial.tools.list_ports.comports()
        values = []
        for p in sorted(ports, key=lambda x: x.device):
            values.append(f'{p.device} - {p.description}')
        self._port_combo['values'] = values
        if values:
            self._port_combo.current(0)

    def get_selected_port(self) -> str | None:
        text = self._port_var.get()
        if not text:
            return None
        return text.split(' - ')[0].strip()

    def update_status(self, status: ConnectionStatus) -> None:
        self._status = status
        self._draw_status()

    def _draw_status(self):
        self._status_canvas.delete('all')
        color_map = {
            ConnectionStatus.DISCONNECTED: '#888888',
            ConnectionStatus.CONNECTING: '#DDAA00',
            ConnectionStatus.CONNECTED: '#00CC00',
            ConnectionStatus.ERROR: '#CC0000',
        }
        text_map = {
            ConnectionStatus.DISCONNECTED: '未连接',
            ConnectionStatus.CONNECTING: '连接中...',
            ConnectionStatus.CONNECTED: '已连接',
            ConnectionStatus.ERROR: '连接错误',
        }
        color = color_map.get(self._status, '#888888')
        self._status_canvas.create_oval(2, 2, 14, 14, fill=color, outline='')
        self._status_label.config(text=text_map.get(self._status, '未知'))

    def _on_connect(self) -> None:
        self.update_status(ConnectionStatus.CONNECTING)
        port = self.get_selected_port()
        self._worker.connect(port)

    def _on_disconnect(self) -> None:
        self._worker.disconnect()
