#!/usr/bin/env python3
"""Murideo Serial 波特率扫描 + 命令格式测试

串口连接成功但无响应时，逐个波特率尝试发送命令，寻找正确的波特率。
同时测试不同的命令行尾格式。

Usage:
    python tools/test_murideo_scan_baudrate.py COM13
    python tools/test_murideo_scan_baudrate.py COM13 9600
"""

import serial
import sys
import time


BAUDRATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800]

# 不同的命令行尾格式
COMMAND_FORMATS = [
    ('\r\nSENDSINGLE||111,0\r\n', '\\r\\n ... \\r\\n (标准格式)'),
    ('SENDSINGLE||111,0\r\n', '无前导\\r\\n'),
    ('SENDSINGLE||111,0\n', '仅 \\n'),
    ('SENDSINGLE||111,0\r', '仅 \\r'),
    ('\r\nSENDSINGLE||111,0\n', '\\r\\n 前 + \\n 后'),
    ('SENDSINGLE||111,0\r\n\r\n', '双 \\r\\n 结尾'),
]


def try_command(ser, cmd_str, timeout=2.0):
    """发送命令并返回原始响应字节。"""
    ser.reset_input_buffer()
    ser.write(cmd_str.encode('utf-8'))
    ser.flush()
    time.sleep(0.05)

    buf = b''
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if ser.in_waiting > 0:
            chunk = ser.read(min(ser.in_waiting, 4096))
            buf += chunk
        else:
            if buf:
                time.sleep(0.1)
                if ser.in_waiting == 0:
                    break
            else:
                time.sleep(0.05)
    return buf


def scan_baudrate(port, target_baud=None):
    bauds = [target_baud] if target_baud else BAUDRATES

    for baud in bauds:
        print(f'\n{"="*60}')
        print(f'波特率: {baud}')
        print(f'{"="*60}')

        try:
            ser = serial.Serial(
                port=port, baudrate=baud,
                bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0, write_timeout=2.0,
            )
        except serial.SerialException as e:
            print(f'  ❌ 无法打开: {e}')
            continue

        time.sleep(0.1)
        # 排空
        if ser.in_waiting:
            junk = ser.read(ser.in_waiting)
            print(f'  排空 {len(junk)} 字节: {junk.hex(" ")}')

        found_response = False

        for cmd, desc in COMMAND_FORMATS:
            raw = try_command(ser, cmd, timeout=2.0)

            if raw:
                text = raw.decode('utf-8', errors='replace')
                has_response = 'RESPONSE' in text
                has_echo = '||' in text and 'RESPONSE' not in text

                status = '✅' if has_response else ('🔄 有回显' if has_echo else '📦 有数据')
                print(f'  {status} [{desc}]')
                print(f'    命令: {repr(cmd)}')
                print(f'    响应 ({len(raw)} 字节): {repr(text[:200])}')
                print(f'    十六进制: {raw[:80].hex(" ")}')

                if has_response:
                    found_response = True
            else:
                print(f'  ❌ [{desc}] 无响应')

        # 如果标准格式都没响应，尝试只读（设备可能在主动发送数据）
        if not found_response:
            print(f'\n  --- 尝试纯监听（不发命令，等3秒）---')
            ser.reset_input_buffer()
            time.sleep(3.0)
            if ser.in_waiting:
                raw = ser.read(ser.in_waiting)
                text = raw.decode('utf-8', errors='replace')
                print(f'  📦 收到 {len(raw)} 字节主动数据: {repr(text[:200])}')
                print(f'  十六进制: {raw[:80].hex(" ")}')
            else:
                print(f'  ❌ 无主动数据')

        ser.close()

    # 汇总
    print(f'\n{"="*60}')
    print(f'扫描完成。如果所有波特率都无响应，可能原因:')
    print(f'  1. 串口号错误（COM13 不是 Murideo）')
    print(f'  2. Murideo 需要先通过其他方式唤醒串口')
    print(f'  3. 串口线只连了 TX/RX 缺 GND')
    print(f'  4. 设备串口协议与 WebSocket 协议不同')
    print(f'{"="*60}')


if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM3'
    target_baud = int(sys.argv[2]) if len(sys.argv) > 2 else None
    scan_baudrate(port, target_baud)
