import json
import os
import sys


def _app_data_dir() -> str:
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
        return os.path.join(base, 'ca410_reader')
    return os.path.expanduser('~/.ca410_reader')


class AppConfig:
    """Persistent user preferences."""

    CONFIG_DIR = _app_data_dir()
    CONFIG_FILE = 'config.json'

    DEFAULTS = {
        'last_port': None,
        'mode': 'xyLv',
        'continuous_interval': 1.0,
        'window_geometry': '900x650',
        'murideo_host': '192.168.1.239',
        'murideo_transport': 'websocket',
        'murideo_serial_port': '',
        'murideo_serial_baudrate': 115200,
    }

    def __init__(self):
        self._data = dict(self.DEFAULTS)

    @property
    def last_port(self) -> str | None:
        return self._data['last_port']

    @last_port.setter
    def last_port(self, value: str | None) -> None:
        self._data['last_port'] = value

    @property
    def mode(self) -> str:
        return self._data['mode']

    @mode.setter
    def mode(self, value: str) -> None:
        self._data['mode'] = value

    @property
    def continuous_interval(self) -> float:
        return self._data['continuous_interval']

    @continuous_interval.setter
    def continuous_interval(self, value: float) -> None:
        self._data['continuous_interval'] = value

    @property
    def window_geometry(self) -> str:
        return self._data['window_geometry']

    @window_geometry.setter
    def window_geometry(self, value: str) -> None:
        self._data['window_geometry'] = value

    @property
    def murideo_host(self) -> str:
        return self._data.get('murideo_host', '')

    @murideo_host.setter
    def murideo_host(self, value: str) -> None:
        self._data['murideo_host'] = value

    @property
    def murideo_transport(self) -> str:
        return self._data.get('murideo_transport', 'websocket')

    @murideo_transport.setter
    def murideo_transport(self, value: str) -> None:
        self._data['murideo_transport'] = value

    @property
    def murideo_serial_port(self) -> str:
        return self._data.get('murideo_serial_port', '')

    @murideo_serial_port.setter
    def murideo_serial_port(self, value: str) -> None:
        self._data['murideo_serial_port'] = value

    @property
    def murideo_serial_baudrate(self) -> int:
        return self._data.get('murideo_serial_baudrate', 115200)

    @murideo_serial_baudrate.setter
    def murideo_serial_baudrate(self, value: int) -> None:
        self._data['murideo_serial_baudrate'] = value

    @classmethod
    def load(cls) -> 'AppConfig':
        cfg = cls()
        path = os.path.join(cls.CONFIG_DIR, cls.CONFIG_FILE)
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                cfg._data.update({k: v for k, v in saved.items() if k in cls.DEFAULTS})
            except Exception:
                pass
        return cfg

    def save(self) -> None:
        try:
            os.makedirs(self.CONFIG_DIR, exist_ok=True)
            path = os.path.join(self.CONFIG_DIR, self.CONFIG_FILE)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
