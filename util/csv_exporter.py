import csv
from datetime import datetime


def export_to_csv(data: list[dict], headers: list[str], filepath: str) -> None:
    if not data:
        return
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)


def prompt_save_path(parent) -> str | None:
    import tkinter.filedialog as fd
    filepath = fd.asksaveasfilename(
        parent=parent,
        defaultextension='.csv',
        filetypes=[('CSV 文件', '*.csv'), ('所有文件', '*.*')],
        initialfile=f'ca410_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
    )
    return filepath if filepath else None
