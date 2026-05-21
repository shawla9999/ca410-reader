import tkinter as tk
from tkinter import ttk

from driver.ca410_types import MeasurementMode, TduvLvResult, XyLvResult
from ui.fonts import mono_family, cjk_family


class MeasurementPanel(ttk.Frame):
    """Compact single-row display for current measurement values."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._mode = MeasurementMode.XY_LV
        self._create_widgets()

    def _create_widgets(self):
        self._fields = {}
        fields_xy = [('lv', 'Lv', 'cd/m²'), ('x', 'x', ''), ('y', 'y', '')]
        fields_tduv = [('lv', 'Lv', 'cd/m²'), ('tcp', 'Tcp', 'K'), ('duv', 'duv', '')]

        row = ttk.Frame(self)
        row.pack(fill=tk.X, padx=10, pady=6)

        for i, (key, label, unit) in enumerate(fields_xy + fields_tduv[1:]):
            if key in self._fields:
                continue
            if i > 0:
                ttk.Separator(row, orient=tk.VERTICAL).pack(
                    side=tk.LEFT, fill=tk.Y, padx=8, pady=2
                )
            lbl = ttk.Label(row, text=f'{label}:', font=(cjk_family(), 11), anchor='e')
            lbl.pack(side=tk.LEFT)
            val = ttk.Label(row, text='---', font=(mono_family(), 18, 'bold'), width=10, anchor='center')
            val.pack(side=tk.LEFT, padx=(2, 0))
            unit_lbl = ttk.Label(row, text=unit, font=(cjk_family(), 10), anchor='w')
            unit_lbl.pack(side=tk.LEFT, padx=(2, 0))
            self._fields[key] = {'label': lbl, 'value': val, 'unit': unit_lbl}

        self._apply_mode_visibility()

    def update_values(self, result: XyLvResult | TduvLvResult) -> None:
        self._fields['lv']['value'].config(text=f'{result.lv:.2f}')

        if isinstance(result, TduvLvResult):
            self._mode = MeasurementMode.TDUV_LV
            self._fields['tcp']['value'].config(text=f'{result.tcp:.0f}')
            self._fields['duv']['value'].config(text=f'{result.duv:.4f}')
        else:
            self._mode = MeasurementMode.XY_LV
            self._fields['x']['value'].config(text=f'{result.x:.4f}')
            self._fields['y']['value'].config(text=f'{result.y:.4f}')

        self._apply_mode_visibility()

    def clear_values(self) -> None:
        for key in self._fields:
            self._fields[key]['value'].config(text='---')

    def set_mode(self, mode: MeasurementMode) -> None:
        self._mode = mode
        self._apply_mode_visibility()

    def _apply_mode_visibility(self) -> None:
        if self._mode == MeasurementMode.TDUV_LV:
            for w in self._fields['x'].values():
                w.pack_forget()
            for w in self._fields['y'].values():
                w.pack_forget()
            for w in self._fields['tcp'].values():
                w.pack(side=tk.LEFT)
            for w in self._fields['duv'].values():
                w.pack(side=tk.LEFT)
        else:
            for w in self._fields['tcp'].values():
                w.pack_forget()
            for w in self._fields['duv'].values():
                w.pack_forget()
            for w in self._fields['x'].values():
                w.pack(side=tk.LEFT)
            for w in self._fields['y'].values():
                w.pack(side=tk.LEFT)
