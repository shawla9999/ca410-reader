#!/usr/bin/env python3
"""Step-by-step CA-410 connection test.

Replicates the exact connect() flow to find which command causes ER10.

Usage:
    python tools/test_ca410_connect.py
    python tools/test_ca410_connect.py COM14
"""

import serial
import serial.tools.list_ports
import sys
import time

PORT = sys.argv[1] if len(sys.argv) > 1 else None

COMMANDS = [
    ('COM,1', 'Enter remote mode', 0.5),
    ('PSC,1', 'Select probe 1', 0.2),
    ('MDS,0', 'Set xyLv display mode', 0.3),
    ('MES', 'Trigger measurement', 0.5),
    ('COM,0', 'Exit remote mode', 0.1),
]


def send_recv(ser, cmd, desc, delay_after):
    ser.reset_input_buffer()
    # Drain any leftover data
    if ser.in_waiting:
        junk = ser.read(ser.in_waiting)

    data = cmd + '\r'
    ser.write(data.encode('ascii'))
    ser.flush()
    print(f'  Sent: {cmd!r}  ({desc})')

    time.sleep(delay_after)

    raw = ser.read_until(b'\r')
    if not raw:
        print(f'  -> No response (timeout)')
        return False

    resp = raw.decode('ascii', errors='replace').strip()
    status = 'OK' if resp.startswith('OK') else 'FAIL'
    print(f'  -> {resp!r}  [{status}]')
    return resp.startswith('OK')


def main():
    if not PORT:
        ports = serial.tools.list_ports.comports()
        for p in sorted(ports, key=lambda x: x.device):
            desc = (p.description or '').lower()
            mfg = (p.manufacturer or '').lower()
            if 'konica' in desc or 'ca-410' in desc or 'ca-s40' in desc or 'konica' in mfg or 'measuring' in desc or '132b' in f'{p.vid:#06x}':
                port = p.device
                print(f'Auto-detected: {port} ({p.description})')
                break
        if not port and len(ports) == 1:
            port = ports[0].device
        if not port:
            print('Usage: python tools/test_ca410_connect.py COM14')
            sys.exit(1)
    else:
        port = PORT

    print(f'Port: {port}')
    print(f'Config: 8N1 @ 38400, no flow control')
    print('=' * 50)

    try:
        ser = serial.Serial(
            port=port,
            baudrate=38400,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            rtscts=False,
            dsrdtr=False,
            timeout=2.0,
            write_timeout=2.0,
        )
    except serial.SerialException as e:
        print(f'Failed to open {port}: {e}')
        sys.exit(1)

    print(f'Serial opened: {port}\n')

    for cmd, desc, delay in COMMANDS:
        ok = send_recv(ser, cmd, desc, delay)
        if not ok and cmd == 'COM,0':
            # Exiting remote mode may fail silently, that's OK
            continue
        if not ok:
            print(f'\n*** FAILED at: {cmd} ({desc}) ***')
            # If PSC fails, try without it
            if cmd == 'PSC,1':
                print('\nRetrying without PSC — trying MDS directly...')
                time.sleep(0.3)
                ok = send_recv(ser, 'MDS,0', 'Set xyLv display mode (no PSC)', 0.3)
                if ok:
                    print('MDS succeeded without PSC! Continuing...')
                    ok = send_recv(ser, 'MES', 'Trigger measurement', 0.5)
            break

    ser.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
