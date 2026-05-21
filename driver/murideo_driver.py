"""Driver for Murideo Seven G8K pattern generator.

Protocol reference: murideo-seven-g8k-protocol.md

Supports two transport types:
    - WebSocket: ws://{device_ip}/ws/uart (default, preferred)
    - Serial:    RS-232 or USB virtual COM port (same command format)

Command format (identical for both transports):
    \\r\\n{FUNCTION}||{CATEGORY},{VALUE}\\r\\n

Three command functions:
    SENDSINGLE  — most settings (timing, color space, HDR, etc.)
    SENDDOUBLE  — pattern and audio selection
    SENDOTHER   — special commands (factory reset, IRE/window size)

Categories relevant to this app:
    97  TIMING       SENDSINGLE   (resolution/refresh)
    98  PATTERN      SENDDOUBLE   (test pattern selection)
    99  COLOR_SPACE  SENDSINGLE
   100  COLOR_DEPTH  SENDSINGLE
   101  HDCP         SENDSINGLE
   111  HDR          SENDSINGLE   (0=SDR, 1=HDR10, 2=HLG, 3-10=CUSTOM)
   112  BT2020       SENDSINGLE
 30971  IRE_WINDOW   SENDOTHER    (IRE level + window size)

IRE/Window size command (discovered from Web UI, confirmed by testing):
    1. Send SENDDOUBLE||98,26 to select Window pattern
    2. Wait 700ms
    3. Send SENDOTHER||30971,{ire},{size}
       - ire: IRE brightness level (0-255, 255=full white)
       - size: window size percentage (0-100)

Response format (confirmed by testing):
    RESPONSE||{32768+CATEGORY}||{VALUE}\\r\\n
    e.g. PATTERN (Cat 98) -> RESPONSE||32866||26\\r\\n
    e.g. HDR (Cat 111)    -> RESPONSE||32879||1\\r\\n
"""

import logging

import serial

from driver.murideo_transport import MurideoTransport, WebSocketTransport, SerialTransport

logger = logging.getLogger(__name__)


class MurideoError(Exception):
    """Base exception for Murideo driver errors."""


class MurideoConnectionError(MurideoError):
    """Could not connect to Murideo."""


class MurideoTimeoutError(MurideoError):
    """No response from Murideo within expected time."""


class MurideoCommandError(MurideoError):
    """Murideo rejected a command or returned an error."""


# -- Category constants (from protocol doc) --
CAT_TIMING = 97
CAT_PATTERN = 98
CAT_COLOR_SPACE = 99
CAT_COLOR_DEPTH = 100
CAT_HDCP = 101
CAT_HDMI_DVI = 102
CAT_PCM_SAMPLE_RATE = 103
CAT_PCM_BIT_DEPTH = 104
CAT_DOLBY_DTS = 105
CAT_PCM_CHANNEL = 107
CAT_PCM_VOLUME = 109
CAT_HDR = 111
CAT_BT2020 = 112
CAT_PCM_SINEWAVE = 115
CAT_ARC_EARC = 131
CAT_CEC = 122
CAT_ARC_HPD = 177
CAT_EARC_HPD = 178
CAT_HDMI_5V = 179
CAT_FAN = 30723
CAT_FACTORY_RESET = 30722
CAT_IRE_WINDOW = 30971
CAT_IRE_INIT = 63739

# HDR values
HDR_OFF = 0
HDR_HDR10 = 1
HDR_HLG = 2

# Pattern IDs (from protocol doc)
PATTERN_WINDOW = 26
PATTERN_DVS_WHITE_LEVEL_1 = 50
PATTERN_DVS_WHITE_LEVEL_2 = 51
PATTERN_DVS_WHITE_LEVEL_3 = 52
PATTERN_DVS_WHITE_80_100 = 53
PATTERN_100_COLOR_BARS = 0
PATTERN_WHITE_SCREEN = 11
PATTERN_BLACK_SCREEN = 10

# Response category offset: response_cat = command_cat + 32768
RESPONSE_CAT_OFFSET = 32768


def _build_command(function: str, category: int, value) -> str:
    """Build a Murideo command string."""
    return f'\r\n{function}||{category},{value}\r\n'


def _build_sendsingle(category: int, value) -> str:
    return _build_command('SENDSINGLE', category, value)


def _build_senddouble(category: int, value) -> str:
    return _build_command('SENDDOUBLE', category, value)


def _parse_response(response: str) -> dict | None:
    """Parse a Murideo response string.

    Format: RESPONSE||{response_cat}||{value}\\r\\n
    Returns dict with keys: function, response_cat, value, command_cat
    or None if the response doesn't match expected format.
    """
    if not response:
        return None
    text = response.strip().rstrip('\r\n')
    parts = text.split('||')
    if len(parts) >= 3 and parts[0] == 'RESPONSE':
        try:
            resp_cat = int(parts[1])
            value = parts[2].strip()
            command_cat = resp_cat - RESPONSE_CAT_OFFSET
            return {
                'function': parts[0],
                'response_cat': resp_cat,
                'value': value,
                'command_cat': command_cat,
            }
        except (ValueError, IndexError):
            pass
    return None


class MurideoDriver:
    """Control a Murideo Seven G8K via WebSocket or Serial.

    All methods are blocking and must be called from worker threads
    (not the tkinter main thread).
    """

    DEFAULT_IP = '192.168.1.239'
    WS_PATH = '/ws/uart'
    RECV_TIMEOUT = 2.0

    def __init__(self, transport_type: str = 'websocket'):
        self._host = ''
        self._ws_url = ''
        self._connected = False
        self._transport: MurideoTransport | None = None
        self._transport_type = transport_type
        self._serial_config: dict = {}

    # -- properties ----------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        if self._transport:
            return self._transport.is_connected()
        return self._connected

    @property
    def host(self) -> str:
        return self._host

    @property
    def transport_type(self) -> str:
        return self._transport_type

    @property
    def serial_port(self) -> str:
        return self._serial_config.get('port', '')

    # -- configuration -------------------------------------------------------

    def configure(self, host: str) -> None:
        """Configure WebSocket connection target."""
        self._transport_type = 'websocket'
        self._host = host.strip()
        self._ws_url = f'ws://{self._host}{self.WS_PATH}'

    def configure_serial(self, port: str, baudrate: int = 115200,
                         bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE,
                         stopbits=serial.STOPBITS_ONE) -> None:
        """Configure Serial connection parameters."""
        self._transport_type = 'serial'
        self._serial_config = {
            'port': port, 'baudrate': baudrate,
            'bytesize': bytesize, 'parity': parity, 'stopbits': stopbits,
        }

    # -- connection ----------------------------------------------------------

    def connect(self, host: str | None = None) -> None:
        """Connect to Murideo. Blocks until connected or error."""
        if self._transport_type == 'websocket':
            if host:
                self.configure(host)
            if not self._host:
                raise MurideoConnectionError('请输入 Murideo IP 地址')
            self._transport = WebSocketTransport()
            try:
                self._transport.connect(
                    url=self._ws_url, timeout=self.RECV_TIMEOUT,
                )
                self._connected = True
                logger.info('Connected to Murideo at %s', self._ws_url)
            except Exception as e:
                self._connected = False
                self._transport = None
                raise MurideoConnectionError(
                    f'无法连接到 Murideo ({self._ws_url}): {e}'
                ) from e
        elif self._transport_type == 'serial':
            if not self._serial_config.get('port'):
                raise MurideoConnectionError('请选择 Murideo 串口')
            self._transport = SerialTransport()
            try:
                self._transport.connect(
                    **self._serial_config, timeout=self.RECV_TIMEOUT,
                )
                self._connected = True
                logger.info('Connected to Murideo serial %s',
                            self._serial_config['port'])
            except Exception as e:
                self._connected = False
                self._transport = None
                raise MurideoConnectionError(
                    f'无法打开 Murideo 串口: {e}'
                ) from e
        else:
            raise MurideoConnectionError(
                f'未知传输类型: {self._transport_type}')

    def disconnect(self) -> None:
        """Disconnect from Murideo."""
        if self._transport:
            try:
                self._transport.disconnect()
            except Exception:
                pass
            self._transport = None
        self._connected = False
        logger.info('Disconnected from Murideo')

    # -- high-level: window size / IRE ---------------------------------------

    def set_ire_window(self, ire: int, window_size: int,
                       hdr_mode: int | None = None,
                       bt2020: int | None = None,
                       color_depth: int | None = None,
                       timing: int | None = None,
                       color_space: int | None = None,
                       pattern_id: int | None = None) -> None:
        """Set HDR, IRE brightness level and window size in one connection.

        All commands are sent on a single transport connection because
        the IRE mode state does not persist across connections.

        Sequence:
        1. (optional) Set timing
        2. (optional) Set color space
        3. (optional) Set HDR mode
        4. (optional) Set BT.2020
        5. (optional) Set color depth
        6. Send SENDOTHER||63739 to initialize IRE mode
        7. Send Window pattern (SENDDOUBLE||98,26 or pattern_id)
        8. Wait 700ms
        9. Send SENDOTHER||30971,{IRE},{window_size}

        Args:
            ire: IRE brightness level (0-255, 255=full white)
            window_size: Window size percentage (0-100)
            hdr_mode: Optional HDR mode (0=SDR, 1=HDR10, 2=HLG)
            bt2020: Optional BT.2020 (0=disable, 1=enable)
            color_depth: Optional color depth (0=8bit, 1=10bit, 2=12bit)
            timing: Optional timing ID (e.g. 34=3840x2160@60Hz)
            color_space: Optional color space (0=RGB0-255, 1=RGB16-235, 2-4=YC)
            pattern_id: Optional pattern ID (default 26=Window)
        """
        self._ensure_connected()
        ire = max(0, min(255, int(ire)))
        window_size = max(0, min(100, int(window_size)))
        commands = []
        delays = []
        # Optional: Timing
        if timing is not None:
            commands.append(_build_sendsingle(CAT_TIMING, timing))
            delays.append(0)
        # Optional: Color space
        if color_space is not None:
            commands.append(_build_sendsingle(CAT_COLOR_SPACE, color_space))
            delays.append(0)
        # Optional: HDR mode
        if hdr_mode is not None:
            commands.append(_build_sendsingle(CAT_HDR, hdr_mode))
            delays.append(0)
        # Optional: BT.2020
        if bt2020 is not None:
            commands.append(_build_sendsingle(CAT_BT2020, bt2020))
            delays.append(0)
        # Optional: Color depth
        if color_depth is not None:
            commands.append(_build_sendsingle(CAT_COLOR_DEPTH, color_depth))
            delays.append(0)
        # IRE init (must be sent each time)
        commands.append(f'\r\nSENDOTHER||{CAT_IRE_INIT}\r\n')
        delays.append(0)
        # Window pattern (or custom pattern)
        pid = pattern_id if pattern_id is not None else PATTERN_WINDOW
        commands.append(_build_senddouble(CAT_PATTERN, pid))
        delays.append(0)
        # IRE + window size (after 700ms delay)
        commands.append(f'\r\nSENDOTHER||{CAT_IRE_WINDOW},{ire},{window_size}\r\n')
        delays.append(0.7)
        try:
            self._transport.send_batch(commands, delays, self.RECV_TIMEOUT)
        except Exception as e:
            logger.error('Murideo IRE window error: %s', e)
            raise MurideoError(f'IRE窗口设置失败: {e}') from e

    # -- high-level: brightness / HDR ----------------------------------------

    def set_hdr(self, mode: int) -> None:
        """Set HDR mode. 0=SDR, 1=HDR10, 2=HLG, 3-10=CUSTOM"""
        self._ensure_connected()
        self._send_and_wait(_build_sendsingle(CAT_HDR, mode))

    def set_sdr(self) -> None:
        self.set_hdr(HDR_OFF)

    def set_hdr10(self) -> None:
        self.set_hdr(HDR_HDR10)

    def set_hlg(self) -> None:
        self.set_hdr(HDR_HLG)

    # -- high-level: timing ---------------------------------------------------

    def set_timing(self, timing_id: int) -> None:
        """Set video timing. Common: 34=3840x2160@60Hz, 20=1080p@60Hz."""
        self._ensure_connected()
        self._send_and_wait(_build_sendsingle(CAT_TIMING, timing_id))

    # -- high-level: pattern --------------------------------------------------

    def set_pattern(self, pattern_id: int) -> None:
        """Set test pattern. Common: 0=ColorBars, 11=White, 26=Window."""
        self._ensure_connected()
        self._send_and_wait(_build_senddouble(CAT_PATTERN, pattern_id))

    # -- high-level: color space / depth --------------------------------------

    def set_color_space(self, value: int) -> None:
        """0=RGB(0-255), 1=RGB(16-235), 2=YC444, 3=YC422, 4=YC420"""
        self._ensure_connected()
        self._send_and_wait(_build_sendsingle(CAT_COLOR_SPACE, value))

    def set_color_depth(self, value: int) -> None:
        """0=8Bit, 1=10Bit, 2=12Bit, 3=16Bit"""
        self._ensure_connected()
        self._send_and_wait(_build_sendsingle(CAT_COLOR_DEPTH, value))

    # -- high-level: bulk operations ------------------------------------------

    def write_all(self, hdr_mode: int | None = None,
                  pattern_id: int | None = None) -> dict:
        """Set HDR mode and/or pattern on Murideo."""
        result: dict = {}
        if hdr_mode is not None:
            try:
                self.set_hdr(hdr_mode)
                result['hdr_mode'] = True
            except MurideoError as e:
                result['hdr_mode_error'] = str(e)
        if pattern_id is not None:
            try:
                self.set_pattern(pattern_id)
                result['pattern'] = True
            except MurideoError as e:
                result['pattern_error'] = str(e)
        return result

    # -- raw command ----------------------------------------------------------

    def send_command(self, command: str) -> str | None:
        """Send a raw command string and return the response."""
        self._ensure_connected()
        return self._send_and_wait(command)

    def send_sendsingle(self, category: int, value) -> str | None:
        return self.send_command(_build_sendsingle(category, value))

    def send_senddouble(self, category: int, value) -> str | None:
        return self.send_command(_build_senddouble(category, value))

    def send_sendother(self, category: int, *values) -> str | None:
        args = ','.join(str(v) for v in values)
        cmd = f'\r\nSENDOTHER||{category},{args}\r\n'
        return self.send_command(cmd)

    # -- internal -------------------------------------------------------------

    def _send_and_wait(self, command: str) -> str | None:
        """Send a command via the transport and wait for response."""
        self._ensure_connected()
        try:
            return self._transport.send_and_recv(command, self.RECV_TIMEOUT)
        except ConnectionError as e:
            self._connected = False
            raise MurideoConnectionError(f'连接已断开: {e}') from e
        except Exception as e:
            logger.error('Murideo send error: %s', e)
            raise MurideoError(f'发送命令失败: {e}') from e

    def _ensure_connected(self) -> None:
        if not self._transport or not self._transport.is_connected():
            self._connected = False
            raise MurideoConnectionError('Murideo 未连接')
