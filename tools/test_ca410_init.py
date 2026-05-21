#!/usr/bin/env python3
"""Test CA-410 full initialization sequence to find what's missing.

After COM,1 + MDS,0 the device returns ER10 on MES.
The official SDK does: SetConfiguration -> AutoConnect -> (open shutter if no zero cal needed)
This script tries adding shutter open and sync mode setup.

Usage:
    python tools/test_ca410_init.py COM14
"""

import serial
import serial.tools.list_ports
import sys
import time

PORT = sys.argv[1] if len(sys.argv) > 1 else None


def send_recv(ser, cmd, delay=0.3):
    ser.reset_input_buffer()
    if ser.in_waiting:
        ser.read(ser.in_waiting)
    data = cmd + '\r'
    ser.write(data.encode('ascii'))
    ser.flush()
    time.sleep(delay)
    raw = ser.read_until(b'\r')
    if not raw:
        return None
    return raw.decode('ascii', errors='replace').strip()


def test_sequence(port):
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
    print(f'Serial opened: {port}')

    def try_cmd(cmd, desc, delay=0.3):
        resp = send_recv(ser, cmd, delay)
        status = 'OK' if resp and resp.startswith('OK') else 'FAIL'
        print(f'  {cmd:20s} ({desc:30s}) -> {resp!r:30s} [{status}]')
        return resp

    # Step 1: Enter remote mode
    print('\n--- Step 1: Enter remote mode ---')
    try_cmd('COM,1', 'Enter remote mode', 0.5)

    # Step 2: Try various initialization commands
    print('\n--- Step 2: Initialization commands ---')

    # Try shutter open (SHU command)
    try_cmd('SHU,1', 'Open shutter (SHU,1)', 0.3)
    try_cmd('SHU', 'Open shutter (SHU)', 0.3)

    # Try sync mode - NTSC (SYN,0)
    try_cmd('SYN,0', 'Sync mode NTSC (SYN,0)', 0.3)

    # Try averaging mode - FAST (AVR,1)
    try_cmd('AVR,1', 'Averaging FAST (AVR,1)', 0.3)

    # Try display mode
    try_cmd('MDS,0', 'Display mode xyLv (MDS,0)', 0.3)

    # Step 3: Try MES
    print('\n--- Step 3: Try measurement ---')
    resp = try_cmd('MES', 'Trigger measurement', 1.0)

    if resp and resp.startswith('OK'):
        print('\n*** MEASUREMENT SUCCESS! ***')
    else:
        # If still failing, try more commands
        print('\n--- Still failing. Trying more init commands ---')

        # Try DMM (Display Measurement Mode?)
        try_cmd('DMM,0', 'DMM 0', 0.3)

        # Try RNM (Range Mode?)
        try_cmd('RNM,0', 'Range auto (RNM,0)', 0.3)

        # Try ZRC (zero calibration) - might be required
        print('\n--- Try zero calibration first ---')
        try_cmd('ZRC', 'Zero calibration', 3.0)

        # Try MES again
        resp = try_cmd('MES', 'Measurement after ZRC', 1.0)
        if resp and resp.startswith('OK'):
            print('\n*** MEASUREMENT SUCCESS AFTER ZERO CAL! ***')

    # Cleanup
    try_cmd('COM,0', 'Exit remote mode', 0.3)
    ser.close()
    print('\nDone.')


def main():
    port = PORT
    if not port:
        ports = serial.tools.list_ports.comports()
        for p in sorted(ports, key=lambda x: x.device):
            desc = (p.description or '').lower()
            mfg = (p.manufacturer or '').lower()
            if 'konica' in desc or 'ca-410' in desc or 'measuring' in desc or '132b' in f'{p.vid:#06x}':
                port = p.device
                print(f'Auto-detected: {port} ({p.description})')
                break
        if not port and len(ports) == 1:
            port = ports[0].device
        if not port:
            print('Usage: python tools/test_ca410_init.py COM14')
            sys.exit(1)

    test_sequence(port)


if __name__ == '__main__':
    main()
