from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum


class MeasurementMode(IntEnum):
    XY_LV = 0
    TDUV_LV = 2


class ConnectionStatus(IntEnum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    ERROR = 3


IMAGE_MODES = ['标准', '影院', '电脑', '鲜艳']

PEAK_BRIGHTNESS_MODES = ['关', '弱', '中', '强']

LOCAL_DIMMING_MODES = ['关', '弱', '中', '强']

HDR_SDR_MODES = ['HDR', 'SDR']


@dataclass
class XyLvResult:
    lv: float
    x: float
    y: float
    timestamp: datetime = field(default_factory=datetime.now)
    image_mode: str = ''
    window_ratio: float | None = None
    window_brightness: float | None = None
    peak_brightness: str = ''
    backlight_value: float | None = None
    local_dimming: str = ''
    hdr_sdr: str = ''
    note: str = ''


@dataclass
class TduvLvResult:
    lv: float
    tcp: float
    duv: float
    timestamp: datetime = field(default_factory=datetime.now)
    image_mode: str = ''
    window_ratio: float | None = None
    window_brightness: float | None = None
    peak_brightness: str = ''
    backlight_value: float | None = None
    local_dimming: str = ''
    hdr_sdr: str = ''
    note: str = ''


MODE_LABELS = {
    MeasurementMode.XY_LV: 'xyLv',
    MeasurementMode.TDUV_LV: 'TduvLv',
}
