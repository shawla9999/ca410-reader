import logging

import serial
import serial.tools.list_ports

from .ca410_types import MeasurementMode, TduvLvResult, XyLvResult
from .errors import CA410Error, ConnectionError, TimeoutError, parse_error_response

logger = logging.getLogger(__name__)


class CA410Driver:
    """Low-level driver for Konica Minolta CA-410 via CA-S40 serial protocol."""

    BAUDRATE = 38400
    BYTESIZE = serial.SEVENBITS
    PARITY = serial.PARITY_EVEN
    STOPBITS = serial.STOPBITS_TWO
    TIMEOUT = 2.0

    def __init__(self, port: str | None = None):
        self._port = port
        self._serial: serial.Serial | None = None
        self._in_remote_mode = False
        self._current_mode: MeasurementMode | None = None

    def discover_port(self) -> str | None:
        """Scan serial ports for CA-410."""
        ports = serial.tools.list_ports.comports()
        for p in ports:
            desc = (p.description or '').lower()
            mfg = (p.manufacturer or '').lower()
            if 'konica' in desc or 'ca-410' in desc or 'ca-s40' in desc:
                logger.info('Auto-discovered CA-410 on %s (%s)', p.device, p.description)
                return p.device
            if 'konica' in mfg:
                logger.info('Auto-discovered CA-410 on %s (manufacturer: %s)', p.device, p.manufacturer)
                return p.device
        if len(ports) == 1:
            logger.info('Only one COM port found: %s', ports[0].device)
            return ports[0].device
        return None

    def connect(self, port: str | None = None) -> None:
        """Open serial connection and enter remote mode."""
        resolved_port = port or self._port
        if not resolved_port:
            resolved_port = self.discover_port()
        if not resolved_port:
            raise ConnectionError('未找到 CA-410 设备，请手动选择串口')

        try:
            self._serial = serial.Serial(
                port=resolved_port,
                baudrate=self.BAUDRATE,
                bytesize=self.BYTESIZE,
                parity=self.PARITY,
                stopbits=self.STOPBITS,
                rtscts=True,
                dsrdtr=False,
                timeout=self.TIMEOUT,
                write_timeout=self.TIMEOUT,
            )
            self._port = resolved_port
            logger.info('Serial port opened: %s', resolved_port)
        except serial.SerialException as e:
            raise ConnectionError(f'无法打开串口 {resolved_port}: {e}') from e

        try:
            self._send_command('COM,1')
            resp = self._read_response()
            self._check_ok(resp)
            self._in_remote_mode = True
            self._current_mode = MeasurementMode.XY_LV
            logger.info('Entered remote mode')
        except CA410Error:
            self._serial.close()
            self._serial = None
            raise

    def disconnect(self) -> None:
        """Exit remote mode and close serial connection."""
        if self._serial is None:
            return
        try:
            if self._in_remote_mode:
                self._send_command('COM,0')
                try:
                    resp = self._read_response()
                    self._check_ok(resp)
                except Exception:
                    pass
                self._in_remote_mode = False
        finally:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
            self._current_mode = None
            logger.info('Disconnected')

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open and self._in_remote_mode

    def set_mode(self, mode: MeasurementMode) -> None:
        """Set measurement display mode."""
        self._ensure_connected()
        if self._current_mode == mode:
            return
        self._send_command(f'MDS,{mode.value}')
        resp = self._read_response()
        self._check_ok(resp)
        self._current_mode = mode
        import time
        time.sleep(0.1)
        logger.info('Mode set to %s', mode.name)

    def measure(self) -> XyLvResult | TduvLvResult:
        """Trigger a measurement and return parsed result."""
        self._ensure_connected()
        self._send_command('MES')
        resp = self._read_response()
        logger.info('Measurement response: %s', resp)
        return self._parse_measurement(resp)

    def zero_calibrate(self) -> None:
        """Perform zero calibration."""
        self._ensure_connected()
        self._send_command('ZRC')
        resp = self._read_response()
        self._check_ok(resp)
        logger.info('Zero calibration completed')

    def _ensure_connected(self) -> None:
        if not self.is_connected:
            raise ConnectionError('CA-410 未连接')

    def _send_command(self, command: str) -> None:
        if self._serial is None:
            raise ConnectionError('串口未打开')
        data = command + '\r'
        self._serial.reset_input_buffer()
        self._serial.write(data.encode('ascii'))
        self._serial.flush()
        logger.debug('Sent: %s', command)

    def _read_response(self) -> str:
        if self._serial is None:
            raise ConnectionError('串口未打开')
        raw = self._serial.read_until(b'\r')
        if not raw:
            raise TimeoutError('设备无响应 (超时)')
        resp = raw.decode('ascii', errors='replace').strip()
        logger.debug('Received: %s', resp)
        return resp

    def _check_ok(self, response: str) -> None:
        if response.startswith('ER'):
            raise parse_error_response(response)
        if not response.startswith('OK'):
            raise CA410Error(f'意外响应: {response}')

    def _parse_measurement(self, response: str) -> XyLvResult | TduvLvResult:
        if response.startswith('ER'):
            raise parse_error_response(response)

        # CA-410 measurement response format observed from real device:
        #   xyLv mode:   OK00,P1 230;182;12.4
        #     - x and y are sent WITHOUT "0." prefix (e.g. "230" = 0.230)
        #     - Lv has decimal point (e.g. "12.4")
        #     - Order: x; y; Lv
        #   TduvLv mode: OK00,P1 0.000;0.000;0.000
        #     - All values have decimal points
        #     - Order: Lv; Tcp; duv
        #   XYZ mode:    OK00,P1 0.000;0.000;0.000
        #     - All values have decimal points
        #     - Order: X; Y; Z
        # Separator: semicolons between values, space after Pn
        # Some firmware versions use commas instead.
        try:
            header, _, data_part = response.partition(',')
            if not data_part:
                raise CA410Error(f'响应格式错误: {response}')

            # Strip the "Pn" prefix (e.g. "P1 ")
            if data_part.startswith('P'):
                probe_end = 0
                for i, c in enumerate(data_part):
                    if c in (' ', ';', ','):
                        probe_end = i
                        break
                if probe_end > 0:
                    values_str = data_part[probe_end:].strip()
                else:
                    values_str = data_part[1:].strip()
            else:
                values_str = data_part.strip()

            # Split values by semicolon or comma
            if ';' in values_str:
                value_parts = values_str.split(';')
            else:
                value_parts = values_str.split(',')

            raw_values = [v.strip() for v in value_parts if v.strip()]
        except (ValueError, IndexError) as e:
            raise CA410Error(f'无法解析测量值: {response}') from e

        if len(raw_values) < 3:
            raise CA410Error(f'数据不足: {response}')

        mode = self._current_mode or MeasurementMode.XY_LV

        if mode == MeasurementMode.XY_LV:
            # xyLv: order is x; y; Lv
            # x and y may lack "0." prefix (e.g. "230" means 0.230)
            x_str, y_str, lv_str = raw_values[0], raw_values[1], raw_values[2]
            x = self._parse_chromaticity(x_str)
            y = self._parse_chromaticity(y_str)
            lv = float(lv_str)
            return XyLvResult(lv=lv, x=x, y=y)
        elif mode == MeasurementMode.TDUV_LV:
            # TduvLv: order is Lv; Tcp; duv (all have decimal points)
            lv = float(raw_values[0])
            tcp = float(raw_values[1])
            duv = float(raw_values[2])
            return TduvLvResult(lv=lv, tcp=tcp, duv=duv)
        else:
            # XYZ or other modes: assume all values have decimal points
            values = [float(v) for v in raw_values]
            return XyLvResult(lv=values[1] if len(values) > 1 else 0.0,
                              x=values[0], y=values[2] if len(values) > 2 else 0.0)

    @staticmethod
    def _parse_chromaticity(s: str) -> float:
        """Parse a chromaticity value (x or y) from CA-410 response.

        The CA-410 omits the "0." prefix for chromaticity values:
        "230" -> 0.230, "1828" -> 0.1828, "0.2305" -> 0.2305
        """
        s = s.strip()
        if '.' in s:
            return float(s)
        # No decimal point: add "0." prefix
        return float('0.' + s)
