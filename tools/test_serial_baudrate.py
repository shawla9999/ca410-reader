#!/usr/bin/env python3
"""Diagnose Murideo serial connection — test different baud rates.

Usage:
    python tools/test_serial_baudrate.py COM3
    python tools/test_serial_baudrate.py COM3 115200

Sends a simple command at each baud rate and checks for any response.
"""

import serial
import sys
import time

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM3'
SINGLE_BAUD = int(sys.argv[2]) if len(sys.argv) > 2 else None

BAUDRATES = [9600, 19200, 38400, 57600, 115200, 230400]

# Try different line endings
COMMANDS = [
    ('\r\nSENDSINGLE||111,0\r\n', 'with \\r\\n wrap'),
    ('SENDSINGLE||111,0\r\n', 'without leading \\r\\n'),
    ('SENDSINGLE||111,0\r', 'with \\r only'),
]


def test_baudrate(port, baudrate):
    print(f'\n=== Testing {port} @ {baudrate} baud ===')
    try:
        ser = serial.Serial(
            port=port, baudrate=baudrate,
            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0, write_timeout=2.0,
        )
    except serial.SerialException as e:
        print(f'  Failed to open: {e}')
        return

    time.sleep(0.1)
    # Drain any existing data
    if ser.in_waiting:
        junk = ser.read(ser.in_waiting)
        print(f'  Drained {len(junk)} bytes of existing data: {repr(junk[:100])}')

    for cmd, desc in COMMANDS:
        ser.reset_input_buffer()
        ser.write(cmd.encode('utf-8'))
        ser.flush()
        print(f'  Sent ({desc}): {repr(cmd)}')

        # Wait and read response
        time.sleep(0.5)
        response = b''
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if ser.in_waiting:
                chunk = ser.read(min(ser.in_waiting, 4096))
                response += chunk
            else:
                if response:
                    break
                time.sleep(0.1)

        if response:
            text = response.decode('utf-8', errors='replace')
            print(f'  Response: {repr(text)}')
        else:
            print(f'  No response (timeout)')

    ser.close()


if __name__ == '__main__':
    if SINGLE_BAUD:
        test_baudrate(PORT, SINGLE_BAUD)
    else:
        for baud in BAUDRATES:
            test_baudrate(PORT, baud)
