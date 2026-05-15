import tkinter as tk
from tkinter import ttk

from driver.ca410_types import MeasurementMode, TduvLvResult, XyLvResult
from ui.fonts import value_font, label_font, unit_font


class MeasurementPanel(ttk.LabelFrame):
    """Large display area for current measurement values."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text='测量结果', **kwargs)
        self._mode = MeasurementMode.XY_LV
        self._create_widgets()

    def _create_widgets(self):
        self._rows = {}
        fields = [
            ('lv', 'Lv', 'cd/m²'),
            ('x', 'x', ''),
            ('y', 'y', ''),
            ('tcp', 'Tcp', 'K'),
            ('duv', 'duv', ''),
        ]
        for i, (key, label, unit) in enumerate(fields):
            lbl = ttk.Label(self, text=f'{label}:', font=label_font(), anchor='e', width=5)
            lbl.grid(row=i, column=0, padx=(10, 5), pady=4, sticky='e')

            val = ttk.Label(self, text='---', font=value_font(), anchor='center', width=14)
            val.grid(row=i, column=1, padx=5, pady=4, sticky='ew')

            unit_lbl = ttk.Label(self, text=unit, font=unit_font(), anchor='w')
            unit_lbl.grid(row=i, column=2, padx=(5, 10), pady=4, sticky='w')

            self._rows[key] = {'label': lbl, 'value': val, 'unit': unit_lbl}

        self.columnconfigure(1, weight=1)
        self._apply_mode_visibility()

    def update_values(self, result: XyLvResult | TduvLvResult) -> None:
        self._rows['lv']['value'].config(text=f'{result.lv:.2f}')

        if isinstance(result, TduvLvResult):
            self._mode = MeasurementMode.TDUV_LV
            self._rows['tcp']['value'].config(text=f'{result.tcp:.0f}')
            self._rows['duv']['value'].config(text=f'{result.duv:.4f}')
        else:
            self._mode = MeasurementMode.XY_LV
            self._rows['x']['value'].config(text=f'{result.x:.4f}')
            self._rows['y']['value'].config(text=f'{result.y:.4f}')

        self._apply_mode_visibility()

    def clear_values(self) -> None:
        for key in self._rows:
            self._rows[key]['value'].config(text='---')

    def set_mode(self, mode: MeasurementMode) -> None:
        self._mode = mode
        self._apply_mode_visibility()

    def _apply_mode_visibility(self) -> None:
        if self._mode == MeasurementMode.TDUV_LV:
            self._rows['x']['label'].grid_remove()
            self._rows['x']['value'].grid_remove()
            self._rows['x']['unit'].grid_remove()
            self._rows['y']['label'].grid_remove()
            self._rows['y']['value'].grid_remove()
            self._rows['y']['unit'].grid_remove()
            self._rows['tcp']['label'].grid()
            self._rows['tcp']['value'].grid()
            self._rows['tcp']['unit'].grid()
            self._rows['duv']['label'].grid()
            self._rows['duv']['value'].grid()
            self._rows['duv']['unit'].grid()
        else:
            self._rows['x']['label'].grid()
            self._rows['x']['value'].grid()
            self._rows['x']['unit'].grid()
            self._rows['y']['label'].grid()
            self._rows['y']['value'].grid()
            self._rows['y']['unit'].grid()
            self._rows['tcp']['label'].grid_remove()
            self._rows['tcp']['value'].grid_remove()
            self._rows['tcp']['unit'].grid_remove()
            self._rows['duv']['label'].grid_remove()
            self._rows['duv']['value'].grid_remove()
            self._rows['duv']['unit'].grid_remove()
