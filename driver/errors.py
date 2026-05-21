class CA410Error(Exception):
    """Base exception for CA-410 driver errors."""


class ConnectionError(CA410Error):
    """Could not open or maintain serial connection."""


class CommandError(CA410Error):
    """Device returned ER00 - command error or communication error."""


class OutOfRangeError(CA410Error):
    """Device returned ER05 - measurement out of range."""


class UndefinedCommandError(CA410Error):
    """Device returned ER10 - undefined command."""


class UnacceptableCommandError(CA410Error):
    """Device returned ER11 - command not acceptable in current state."""


class InvalidDataError(CA410Error):
    """Device returned ER13 - invalid data or parameter."""


class InsufficientProbesError(CA410Error):
    """Device returned ER17 - insufficient probes."""


class NoCalibrationDataError(CA410Error):
    """Device returned ER19 - no valid calibration data."""


class ZeroCalibrationError(CA410Error):
    """Device returned ER21 - zero calibration error."""


class TimeoutError(CA410Error):
    """No response from device within expected time."""


_ERROR_MAP = {
    'ER00': CommandError,
    'ER02': CA410Error,
    'ER05': OutOfRangeError,
    'ER10': UndefinedCommandError,
    'ER11': UnacceptableCommandError,
    'ER13': InvalidDataError,
    'ER17': InsufficientProbesError,
    'ER19': NoCalibrationDataError,
    'ER20': CA410Error,
    'ER21': ZeroCalibrationError,
    'ER30': ZeroCalibrationError,
    'ER31': CA410Error,
    'ER52': CA410Error,
    'ER80': ConnectionError,
    'ER99': CA410Error,
}

_ERROR_MESSAGES = {
    'ER00': '命令错误或通信错误',
    'ER02': '因条件不满足而强制终止测量',
    'ER05': '测量值超出可显示范围 (0.01 - 100,000 cd/m²)',
    'ER10': '未定义命令',
    'ER11': '当前状态下不可接受的命令',
    'ER13': '无效数据或参数',
    'ER17': '探头数量不足',
    'ER19': '无有效校准数据',
    'ER20': '内存数据访问错误',
    'ER21': '零点校准错误 - 请确保探头盖已盖上且无环境光',
    'ER30': '零点校准错误',
    'ER31': '内存写入/读取错误',
    'ER52': 'EEPROM 访问错误',
    'ER80': 'USB 通信错误',
    'ER99': '探头程序错误 (需要固件更新)',
}


def parse_error_response(response: str) -> CA410Error:
    """Parse an 'ERxx' response string into the appropriate exception."""
    code = response.strip()[:4]
    exc_class = _ERROR_MAP.get(code, CA410Error)
    message = _ERROR_MESSAGES.get(code, f'未知设备错误: {code}')
    return exc_class(message)
