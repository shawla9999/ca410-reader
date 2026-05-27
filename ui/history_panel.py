import tkinter as tk
from tkinter import ttk

from driver.ca410_types import MeasurementMode, TduvLvResult, XyLvResult, MODE_LABELS

# CSV headers match Excel "测试用例" sheet exactly
CSV_HEADERS = [
    '编号', '图像模式', '峰值亮度', '对比度增强', 'Local Dimming',
    '小窗口大小', 'HDR/SDR', '白块亮度(nit)',
    'Lv (cd/m²)', 'x', 'y', '备注'
]


class HistoryPanel(ttk.LabelFrame):
    """Scrollable table of measurement history."""

    MAX_ROWS = 1000

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text='历史记录', **kwargs)
        self._count = 0
        self._all_data: list[dict] = []
        self._create_widgets()

    def _create_widgets(self):
        columns = (
            'no', 'image_mode', 'peak_brightness', 'backlight_value', 'local_dimming',
            'window_size', 'hdr_sdr', 'window_brightness',
            'lv', 'x', 'y', 'note',
        )
        self._tree = ttk.Treeview(
            self, columns=columns, show='headings', height=8, selectmode='extended'
        )

        self._tree.heading('no', text='编号')
        self._tree.heading('image_mode', text='图像模式')
        self._tree.heading('peak_brightness', text='峰值亮度')
        self._tree.heading('backlight_value', text='对比度增强')
        self._tree.heading('local_dimming', text='Local Dimming')
        self._tree.heading('window_size', text='小窗口大小')
        self._tree.heading('hdr_sdr', text='HDR/SDR')
        self._tree.heading('window_brightness', text='白块亮度(nit)')
        self._tree.heading('lv', text='Lv (cd/m²)')
        self._tree.heading('x', text='x')
        self._tree.heading('y', text='y')
        self._tree.heading('note', text='备注')

        self._tree.column('no', width=50, anchor='center')
        self._tree.column('image_mode', width=65, anchor='center')
        self._tree.column('peak_brightness', width=65, anchor='center')
        self._tree.column('backlight_value', width=80, anchor='center')
        self._tree.column('local_dimming', width=90, anchor='center')
        self._tree.column('window_size', width=80, anchor='center')
        self._tree.column('hdr_sdr', width=65, anchor='center')
        self._tree.column('window_brightness', width=90, anchor='e')
        self._tree.column('lv', width=85, anchor='e')
        self._tree.column('x', width=65, anchor='e')
        self._tree.column('y', width=65, anchor='e')
        self._tree.column('note', width=120, anchor='w')

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(4, 0))
        ttk.Button(btn_frame, text='清空记录', command=self.clear_history).pack(
            side=tk.LEFT, padx=4
        )

        self._export_callback = None

    def set_export_callback(self, callback) -> None:
        self._export_callback = callback

    def add_entry(self, result: XyLvResult | TduvLvResult) -> None:
        self._count += 1

        if isinstance(result, TduvLvResult):
            x_val = ''
            y_val = ''
        else:
            x_val = f'{result.x:.4f}'
            y_val = f'{result.y:.4f}'

        img_mode = result.image_mode if result.image_mode else ''
        peak = result.peak_brightness if result.peak_brightness else ''
        bl_val = result.backlight_value if result.backlight_value else ''
        ld = result.local_dimming if result.local_dimming else ''
        w_size = f'{result.window_ratio:.0f}%' if result.window_ratio is not None else ''
        hdr = result.hdr_sdr if result.hdr_sdr else ''
        w_bright = f'{result.window_brightness:.0f}' if result.window_brightness is not None else ''
        note = result.note if result.note else ''

        values = (
            f'T{self._count:03d}', img_mode, peak, bl_val, ld,
            w_size, hdr, w_bright,
            f'{result.lv:.2f}', x_val, y_val, note,
        )
        iid = self._tree.insert('', 'end', values=values)
        self._tree.see(iid)

        # Store with header-matching keys for CSV export
        self._all_data.append({
            '编号': f'T{self._count:03d}',
            '图像模式': img_mode,
            '峰值亮度': peak,
            '对比度增强': bl_val,
            'Local Dimming': ld,
            '小窗口大小': w_size,
            'HDR/SDR': hdr,
            '白块亮度(nit)': w_bright,
            'Lv (cd/m²)': f'{result.lv:.2f}',
            'x': x_val,
            'y': y_val,
            '备注': note,
        })

        if len(self._all_data) > self.MAX_ROWS:
            self._all_data.pop(0)
            first = self._tree.get_children()[0]
            self._tree.delete(first)

    def clear_history(self) -> None:
        self._tree.delete(*self._tree.get_children())
        self._all_data.clear()
        self._count = 0

    def get_all_data(self) -> tuple[list[dict], list[str]]:
        return list(self._all_data), CSV_HEADERS

    def _on_export(self) -> None:
        if self._export_callback:
            self._export_callback()
