"""Transport layer for Murideo Seven G8K — abstract base + WebSocket + Serial.

Command format is identical for both transports (WebSocket is a bridge
to the device's internal UART), so only the byte-level I/O differs.
"""

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod

import serial

logger = logging.getLogger(__name__)


class MurideoTransport(ABC):
    """Abstract transport for Murideo command/response protocol."""

    @abstractmethod
    def connect(self, **kwargs) -> None:
        """Open the transport connection."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the transport connection."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the transport is currently connected."""

    @abstractmethod
    def send_and_recv(self, command: str, timeout: float = 5.0) -> str | None:
        """Send a command and return the response string, or None on timeout."""

    @abstractmethod
    def send_batch(self, commands: list[str],
                   delays: list[float] | None = None,
                   timeout: float = 5.0) -> list[str | None]:
        """Send multiple commands on the same connection with optional delays."""


class WebSocketTransport(MurideoTransport):
    """WebSocket transport with persistent connection, heartbeat, and auto-reconnect.

    Runs a dedicated asyncio event loop on a background thread so that
    the WebSocket stays alive between commands. Heartbeat pings keep
    the connection alive; if the connection drops, automatic reconnect
    is attempted up to MAX_RECONNECT times.
    """

    HEARTBEAT_INTERVAL = 30.0
    HEARTBEAT_TIMEOUT = 60.0
    MAX_RECONNECT = 3

    def __init__(self):
        self._url = ''
        self._open_timeout = 5.0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws = None
        self._thread: threading.Thread | None = None
        self._connected_event = threading.Event()
        self._stop_event = threading.Event()
        self._connected = False
        self._reconnect_count = 0

    def connect(self, **kwargs) -> None:
        url = kwargs.get('url', '')
        timeout = kwargs.get('timeout', 5.0)
        if not url:
            raise ValueError('WebSocket URL is required')
        self._url = url
        self._open_timeout = timeout
        self._stop_event.clear()
        self._connected_event.clear()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        if not self._connected_event.wait(timeout=timeout + 5.0):
            self.disconnect()
            raise ConnectionError(f'WebSocket connection timeout: {url}')

    def disconnect(self) -> None:
        self._stop_event.set()
        self._connected = False
        if self._loop and self._loop.is_running():
            # Cancel all tasks on the loop so run_until_complete exits cleanly
            self._loop.call_soon_threadsafe(self._cancel_loop_tasks)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        if self._loop:
            try:
                self._loop.close()
            except Exception:
                pass
        self._loop = None
        self._ws = None
        self._thread = None

    def _cancel_loop_tasks(self) -> None:
        """Cancel all running tasks on the event loop so it can stop."""
        for task in asyncio.all_tasks(self._loop):
            task.cancel()

    def is_connected(self) -> bool:
        return self._connected and self._ws is not None

    def send_and_recv(self, command: str, timeout: float = 5.0) -> str | None:
        if not self._loop or not self._connected:
            raise ConnectionError('WebSocket not connected')
        future = asyncio.run_coroutine_threadsafe(
            self._async_send_and_recv(command, timeout), self._loop,
        )
        try:
            return future.result(timeout=timeout + 2.0)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error('WebSocket send_and_recv error: %s', e)
            return None

    def send_batch(self, commands: list[str],
                   delays: list[float] | None = None,
                   timeout: float = 5.0) -> list[str | None]:
        if not self._loop or not self._connected:
            raise ConnectionError('WebSocket not connected')
        future = asyncio.run_coroutine_threadsafe(
            self._async_send_batch(commands, delays, timeout), self._loop,
        )
        total_delay = sum(d for d in (delays or [])) if delays else 0
        try:
            return future.result(timeout=total_delay + len(commands) * timeout + 5.0)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error('WebSocket send_batch error: %s', e)
            return [None] * len(commands)

    # -- internal: background loop ------------------------------------------

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._ws_lifecycle())
        except asyncio.CancelledError:
            pass
        except RuntimeError:
            pass

    async def _ws_lifecycle(self) -> None:
        """Manage the WebSocket connection with heartbeat and reconnect."""
        import websockets

        while not self._stop_event.is_set():
            try:
                async with websockets.connect(
                    self._url,
                    open_timeout=self._open_timeout,
                    close_timeout=2.0,
                    ping_interval=None,
                ) as ws:
                    self._ws = ws
                    self._connected = True
                    self._reconnect_count = 0
                    self._connected_event.set()
                    logger.info('WebSocket connected to %s', self._url)
                    await self._heartbeat_loop()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._connected = False
                self._connected_event.clear()
                if self._stop_event.is_set():
                    break
                self._reconnect_count += 1
                if self._reconnect_count > self.MAX_RECONNECT:
                    logger.error('WebSocket max reconnect reached: %s', e)
                    break
                backoff = 2 ** (self._reconnect_count - 1)
                logger.warning(
                    'WebSocket disconnected (%s), reconnect %d/%d in %ds',
                    e, self._reconnect_count, self.MAX_RECONNECT, backoff,
                )
                try:
                    await asyncio.wait_for(
                        asyncio.wrap_future(
                            asyncio.run_coroutine_threadsafe(
                                self._wait_stop(backoff), self._loop,
                            )
                        ), timeout=backoff + 1,
                    )
                except (asyncio.TimeoutError, Exception):
                    pass
        self._connected = False

    async def _wait_stop(self, seconds: float) -> None:
        """Wait for stop event or timeout."""
        await asyncio.sleep(seconds)

    async def _heartbeat_loop(self) -> None:
        """Send periodic pings to keep the connection alive."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._ws.ping(), timeout=self.HEARTBEAT_TIMEOUT,
                )
            except Exception:
                logger.debug('WebSocket heartbeat failed')
                break
            try:
                await asyncio.wait_for(
                    asyncio.wrap_future(
                        asyncio.run_coroutine_threadsafe(
                            self._wait_stop(self.HEARTBEAT_INTERVAL), self._loop,
                        )
                    ), timeout=self.HEARTBEAT_INTERVAL + 1,
                )
                if self._stop_event.is_set():
                    break
            except asyncio.TimeoutError:
                pass

    # -- internal: async send/recv ------------------------------------------

    async def _async_send_and_recv(self, command: str,
                                    timeout: float = 5.0) -> str | None:
        if not self._ws:
            raise ConnectionError('WebSocket not connected')
        try:
            await self._ws.send(command)
            logger.debug('WS Sent: %s', repr(command))
            response = await asyncio.wait_for(self._ws.recv(), timeout=timeout)
            logger.debug('WS Received: %s', repr(response))
            return response
        except asyncio.TimeoutError:
            logger.debug('WS: no response (timeout)')
            return None
        except Exception as e:
            self._connected = False
            raise ConnectionError(f'WebSocket send error: {e}') from e

    async def _async_send_batch(self, commands: list[str],
                                 delays: list[float] | None = None,
                                 timeout: float = 5.0) -> list[str | None]:
        if not self._ws:
            raise ConnectionError('WebSocket not connected')
        responses = []
        for i, cmd in enumerate(commands):
            if delays and i < len(delays) and delays[i] > 0:
                await asyncio.sleep(delays[i])
            try:
                await self._ws.send(cmd)
                logger.debug('WS Sent: %s', repr(cmd))
                try:
                    resp = await asyncio.wait_for(
                        self._ws.recv(), timeout=timeout,
                    )
                    logger.debug('WS Received: %s', repr(resp))
                    responses.append(resp)
                except asyncio.TimeoutError:
                    logger.debug('WS: no response (timeout)')
                    responses.append(None)
            except Exception as e:
                self._connected = False
                raise ConnectionError(f'WebSocket batch error: {e}') from e
        return responses


class SerialTransport(MurideoTransport):
    """Serial (RS-232 / USB virtual COM) transport.

    Murideo serial parameters (baud rate etc.) are not documented —
    defaults are 115200/8N1 which is common for modern test equipment.
    All parameters are user-configurable.
    """

    DEFAULT_BAUDRATE = 115200
    DEFAULT_TIMEOUT = 5.0

    def __init__(self):
        self._serial: serial.Serial | None = None
        self._connected = False

    def connect(self, **kwargs) -> None:
        port = kwargs.get('port', '')
        if not port:
            raise ValueError('Serial port is required')
        baudrate = kwargs.get('baudrate', self.DEFAULT_BAUDRATE)
        bytesize = kwargs.get('bytesize', serial.EIGHTBITS)
        parity = kwargs.get('parity', serial.PARITY_NONE)
        stopbits = kwargs.get('stopbits', serial.STOPBITS_ONE)
        timeout = kwargs.get('timeout', self.DEFAULT_TIMEOUT)
        try:
            self._serial = serial.Serial(
                port=port, baudrate=baudrate,
                bytesize=bytesize, parity=parity, stopbits=stopbits,
                timeout=timeout, write_timeout=timeout,
            )
            self._connected = True
            logger.info('Serial connected to %s @ %d', port, baudrate)
            # Handshake: verify device is actually responding
            try:
                handshake_ok = self._handshake(timeout=3.0)
                if not handshake_ok:
                    logger.warning('Serial handshake failed: device not responding')
            except Exception as e:
                logger.warning('Serial handshake error: %s', e)
        except serial.SerialException as e:
            self._connected = False
            self._serial = None
            raise ConnectionError(f'无法打开串口 {port}: {e}') from e

    def _handshake(self, timeout: float = 3.0) -> bool:
        """Send a simple command to verify the Murideo device is responding.

        Sends SENDSINGLE||111,0 (HDR=SDR) and checks for a valid
        RESPONSE. Returns True on success, False on failure.
        """
        cmd = '\r\nSENDSINGLE||111,0\r\n'
        resp = self.send_and_recv(cmd, timeout)
        if resp and 'RESPONSE' in resp:
            logger.info('Serial handshake OK: %s', repr(resp))
            return True
        logger.warning('Serial handshake failed: no valid response (got %s)',
                        repr(resp))
        return False

    def disconnect(self) -> None:
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        self._connected = False
        logger.info('Serial disconnected')

    def is_connected(self) -> bool:
        return (self._connected
                and self._serial is not None
                and self._serial.is_open)

    def send_and_recv(self, command: str, timeout: float = 5.0) -> str | None:
        ser = self._serial
        if not ser or not ser.is_open:
            raise ConnectionError('Serial not connected')
        ser.reset_input_buffer()
        ser.write(command.encode('utf-8'))
        ser.flush()
        logger.debug('Serial Sent: %s', repr(command))
        time.sleep(0.05)
        resp = self._read_response(timeout)
        return resp

    def send_batch(self, commands: list[str],
                   delays: list[float] | None = None,
                   timeout: float = 5.0) -> list[str | None]:
        ser = self._serial
        if not ser or not ser.is_open:
            raise ConnectionError('Serial not connected')
        responses = []
        for i, cmd in enumerate(commands):
            if delays and i < len(delays) and delays[i] > 0:
                time.sleep(delays[i])
            ser.reset_input_buffer()
            ser.write(cmd.encode('utf-8'))
            ser.flush()
            logger.debug('Serial Sent: %s', repr(cmd))
            time.sleep(0.05)
            resp = self._read_response(timeout)
            responses.append(resp)
        return responses

    def _read_response(self, timeout: float = 5.0) -> str | None:
        """Read a complete Murideo response from serial port.

        Handles: echo (device may echo the command), multi-line responses,
        and responses that arrive in fragments.
        Returns the last line containing 'RESPONSE||', or the last line if
        no RESPONSE line found, or None on timeout.
        """
        ser = self._serial
        deadline = time.monotonic() + timeout
        buf = b''
        last_response = None

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            # Check if data is available
            if ser.in_waiting > 0:
                chunk = ser.read(min(ser.in_waiting, 4096))
                buf += chunk
            else:
                # Wait briefly for data
                time.sleep(0.05)
                if ser.in_waiting == 0 and buf:
                    # No more data coming and we have some already
                    break
                continue

            # Process complete lines in buffer
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                line_text = line.decode('utf-8', errors='replace').strip()
                if not line_text:
                    continue
                logger.debug('Serial Received: %s', repr(line_text))
                # Skip echo lines (command sent back by device)
                if '||' in line_text and not line_text.startswith('RESPONSE'):
                    # This looks like an echo of our command, skip it
                    continue
                if line_text.startswith('RESPONSE'):
                    last_response = line_text

        # Process any remaining data in buffer
        if buf:
            line_text = buf.decode('utf-8', errors='replace').strip()
            if line_text:
                logger.debug('Serial Received (partial): %s', repr(line_text))
                if line_text.startswith('RESPONSE'):
                    last_response = line_text
                elif last_response is None:
                    last_response = line_text

        if last_response is None:
            logger.debug('Serial: no response (timeout)')
        return last_response
