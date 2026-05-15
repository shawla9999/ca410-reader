import json
import os


class AppConfig:
    """Persistent user preferences."""

    CONFIG_DIR = os.path.expanduser('~/.ca410_reader')
    CONFIG_FILE = 'config.json'

    DEFAULTS = {
        'last_port': None,
        'mode': 'xyLv',
        'continuous_interval': 1.0,
        'window_geometry': '900x650',
        'murideo_host': '192.168.1.239',
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
