#!/usr/bin/env python3
"""Diagnose CA-410 serial connection — test different configurations.

Usage:
    python tools/diagnose_ca410.py
    python tools/diagnose_ca410.py COM3

Tries multiple serial settings and sends COM,1 to find the working config.
"""

import serial
import serial.tools.list_ports
import sys
import time


CONFIGS = [
    {
        'label': '8N1 (CA-410 official spec)',
        'baudrate': 38400,
        'bytesize': serial.EIGHTBITS,
        'parity': serial.PARITY_NONE,
        'stopbits': serial.STOPBITS_ONE,
        'rtscts': False,
    },
    {
        'label': '8N1 @ 9600',
        'baudrate': 9600,
        'bytesize': serial.EIGHTBITS,
        'parity': serial.PARITY_NONE,
        'stopbits': serial.STOPBITS_ONE,
        'rtscts': False,
    },
    {
        'label': '7E2 (current code setting)',
        'baudrate': 38400,
        'bytesize': serial.SEVENBITS,
        'parity': serial.PARITY_EVEN,
        'stopbits': serial.STOPBITS_TWO,
        'rtscts': True,
    },
    {
        'label': '7E2 no flow control',
        'baudrate': 38400,
        'bytesize': serial.SEVENBITS,
        'parity': serial.PARITY_EVEN,
        'stopbits': serial.STOPBITS_TWO,
        'rtscts': False,
    },
    {
        'label': '8N1 with RTS/CTS',
        'baudrate': 38400,
        'bytesize': serial.EIGHTBITS,
        'parity': serial.PARITY_NONE,
        'stopbits': serial.STOPBITS_ONE,
        'rtscts': True,
    },
]


def list_ports():
    print('=== Available COM ports ===')
    ports = serial.tools.list_ports.comports()
    if not ports:
        print('  No COM ports found!')
        return []
    for p in sorted(ports, key=lambda x: x.device):
        print(f'  {p.device} - {p.description} (VID={p.vid:#06x} PID={p.pid:#06x})')
    return ports


def test_config(port, config):
    label = config.pop('label')
    print(f'\n--- {label} ---')
    try:
        ser = serial.Serial(port=port, timeout=2.0, write_timeout=2.0, dsrdtr=False, **config)
    except serial.SerialException as e:
        print(f'  Failed to open: {e}')
        config['label'] = label
        return False

    time.sleep(0.1)
    if ser.in_waiting:
        junk = ser.read(ser.in_waiting)
        print(f'  Drained {len(junk)} bytes: {repr(junk[:80])}')

    try:
        # Send COM,1 to enter remote mode
        ser.reset_input_buffer()
        cmd = 'COM,1\r'
        ser.write(cmd.encode('ascii'))
        ser.flush()
        print(f'  Sent: {repr(cmd.strip())}')

        time.sleep(1.0)
        raw = ser.read_until(b'\r')
        if not raw:
            print('  No response (timeout)')
            ser.close()
            config['label'] = label
            return False

        resp = raw.decode('ascii', errors='replace').strip()
        print(f'  Response: {repr(resp)}')

        success = resp.startswith('OK')
        if success:
            print('  *** CONNECTION SUCCESS! ***')
            # Try to exit remote mode cleanly
            try:
                ser.reset_input_buffer()
                ser.write(b'COM,0\r')
                ser.flush()
                time.sleep(0.5)
                ser.read_until(b'\r')
            except Exception:
                pass
        ser.close()
        config['label'] = label
        return success

    except Exception as e:
        print(f'  Error: {e}')
        ser.close()
        config['label'] = label
        return False


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else None
    ports = list_ports()

    if not port:
        # Try to auto-detect CA-410
        for p in ports:
            desc = (p.description or '').lower()
            mfg = (p.manufacturer or '').lower()
            if 'konica' in desc or 'ca-410' in desc or 'ca-s40' in desc or 'konica' in mfg:
                port = p.device
                print(f'\nAuto-detected CA-410 on {port}')
                break
        if not port and len(ports) == 1:
            port = ports[0].device
            print(f'\nOnly one COM port, using {port}')
        if not port:
            print('\nNo CA-410 detected. Usage: python tools/diagnose_ca410.py COM3')
            sys.exit(1)

    print(f'\nTesting port: {port}')
    print('=' * 50)

    for config in CONFIGS:
        result = test_config(port, dict(config))
        if result:
            print(f'\n{"=" * 50}')
            print(f'WORKING CONFIG: {config["label"]}')
            cfg = {k: v for k, v in config.items() if k != 'label'}
            print(f'Settings: {cfg}')
            print('=' * 50)
            return

    print(f'\n{"=" * 50}')
    print('No working configuration found.')
    print('Check: 1) CA-410 is powered on  2) USB cable connected  3) COM port is correct')
    print('=' * 50)


if __name__ == '__main__':
    main()
