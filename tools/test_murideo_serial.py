#!/usr/bin/env python3
"""Murideo Serial 通信测试工具

逐条发送命令并验证响应，确认命令是否被设备正确接收。
用于诊断"连接成功但设置失败"的问题。

Usage:
    python tools/test_murideo_serial.py COM3
    python tools/test_murideo_serial.py COM3 115200
    python tools/test_murideo_serial.py /dev/ttyUSB0 9600
"""

import serial
import serial.tools.list_ports
import sys
import time


def list_ports():
    print('可用串口:')
    for p in serial.tools.list_ports.comports():
        print(f'  {p.device}  {p.description}')
    print()


def hex_dump(data: bytes, width=16):
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'  {i:04X}  {hex_part:<{width*3}}  {ascii_part}')
    return '\n'.join(lines)


def read_all(ser, timeout=3.0, label=''):
    """读取串口所有可用数据，返回 (raw_bytes, parsed_text)."""
    buf = b''
    deadline = time.monotonic() + timeout
    first_data = True
    while time.monotonic() < deadline:
        if ser.in_waiting > 0:
            chunk = ser.read(min(ser.in_waiting, 4096))
            buf += chunk
            if first_data and buf:
                print(f'  [{label}] 收到首字节，耗时 {time.monotonic() - (deadline - timeout):.3f}s')
                first_data = False
        else:
            if buf:
                # 已有数据且无更多数据到来，等一小段时间确认
                time.sleep(0.1)
                if ser.in_waiting == 0:
                    break
            else:
                time.sleep(0.05)
    return buf


def parse_response(raw: bytes):
    """解析设备响应，返回 (echo_lines, response_lines)."""
    text = raw.decode('utf-8', errors='replace')
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    echoes = []
    responses = []
    for line in lines:
        if line.startswith('RESPONSE'):
            responses.append(line)
        elif '||' in line:
            echoes.append(line)
        else:
            responses.append(line)
    return echoes, responses, text


def test_single_command(ser, cmd_str, step_name, expect_cat=None, timeout=3.0):
    """发送一条命令并验证响应。

    Args:
        ser: 已打开的 serial.Serial 对象
        cmd_str: 命令字符串（含 \\r\\n）
        step_name: 步骤描述
        expect_cat: 期望的响应 category（用于验证 RESPONSE 格式）
        timeout: 读取超时

    Returns:
        (success: bool, response_text: str)
    """
    print(f'\n--- {step_name} ---')
    print(f'  发送: {repr(cmd_str)}')
    print(f'  十六进制: {cmd_str.encode("utf-8").hex(" ")}')

    ser.reset_input_buffer()
    written = ser.write(cmd_str.encode('utf-8'))
    ser.flush()
    print(f'  已写入 {written} 字节')

    time.sleep(0.05)
    raw = read_all(ser, timeout=timeout, label=step_name)

    if not raw:
        print(f'  ❌ 无响应（超时 {timeout}s）')
        return False, ''

    print(f'  收到 {len(raw)} 字节')
    print(hex_dump(raw))

    echoes, responses, full_text = parse_response(raw)
    if echoes:
        print(f'  回显行:')
        for e in echoes:
            print(f'    {repr(e)}')
    if responses:
        print(f'  响应行:')
        for r in responses:
            print(f'    {repr(r)}')

    # 验证 RESPONSE 格式
    if not responses:
        print(f'  ⚠️ 有数据但无 RESPONSE 行')
        print(f'  原始文本: {repr(full_text)}')
        return False, full_text

    last_resp = responses[-1]
    if not last_resp.startswith('RESPONSE'):
        print(f'  ⚠️ 最后一行不是 RESPONSE: {repr(last_resp)}')
        return False, last_resp

    # 解析 RESPONSE||{cat}||{value}
    parts = last_resp.split('||')
    if len(parts) >= 3:
        try:
            resp_cat = int(parts[1])
            value = parts[2].strip()
            command_cat = resp_cat - 32768
            print(f'  ✅ RESPONSE 解析: cat={command_cat} (resp_cat={resp_cat}), value={value}')
            if expect_cat is not None and command_cat != expect_cat:
                print(f'  ❌ category 不匹配! 期望 {expect_cat}, 实际 {command_cat}')
                return False, last_resp
        except ValueError:
            print(f'  ⚠️ RESPONSE 格式异常: {repr(last_resp)}')
            return False, last_resp
    else:
        print(f'  ⚠️ RESPONSE 字段不足: {repr(last_resp)}')
        return False, last_resp

    return True, last_resp


def run_tests(port: str, baudrate: int):
    print(f'\n{"="*60}')
    print(f'Murideo Serial 通信测试')
    print(f'串口: {port}  波特率: {baudrate}')
    print(f'{"="*60}')

    # 1. 打开串口
    print(f'\n[1] 打开串口...')
    try:
        ser = serial.Serial(
            port=port, baudrate=baudrate,
            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0, write_timeout=2.0,
        )
        print(f'  ✅ 串口已打开: {ser.name}')
        print(f'  配置: {baudrate}/8N1, read_timeout={ser.timeout}s')
    except serial.SerialException as e:
        print(f'  ❌ 无法打开串口: {e}')
        return

    time.sleep(0.1)

    # 排空缓冲区
    if ser.in_waiting:
        junk = ser.read(ser.in_waiting)
        print(f'  排空缓冲区: {len(junk)} 字节')
        print(hex_dump(junk))

    results = {}

    # 2. 测试 HDR 设置 (category=111, 最简单的命令)
    ok, _ = test_single_command(
        ser, '\r\nSENDSINGLE||111,0\r\n',
        '设置 HDR=SDR (111,0)', expect_cat=111,
    )
    results['HDR_SDR'] = ok

    # 等设备处理
    time.sleep(0.3)

    # 3. 测试 HDR=HDR10
    ok, _ = test_single_command(
        ser, '\r\nSENDSINGLE||111,1\r\n',
        '设置 HDR=HDR10 (111,1)', expect_cat=111,
    )
    results['HDR_HDR10'] = ok

    time.sleep(0.3)

    # 4. 测试 Pattern 设置 (category=98, SENDDOUBLE)
    ok, _ = test_single_command(
        ser, '\r\nSENDDOUBLE||98,26\r\n',
        '设置 Pattern=Window (98,26)', expect_cat=98,
    )
    results['Pattern_Window'] = ok

    time.sleep(0.3)

    # 5. 测试 Timing 设置 (category=97)
    ok, _ = test_single_command(
        ser, '\r\nSENDSINGLE||97,34\r\n',
        '设置 Timing=3840x2160@60Hz (97,34)', expect_cat=97,
    )
    results['Timing'] = ok

    time.sleep(0.3)

    # 6. 测试 IRE Init (SENDOTHER||63739)
    print(f'\n--- IRE 初始化 (63739) ---')
    cmd = '\r\nSENDOTHER||63739\r\n'
    print(f'  发送: {repr(cmd)}')
    ser.reset_input_buffer()
    written = ser.write(cmd.encode('utf-8'))
    ser.flush()
    print(f'  已写入 {written} 字节')

    time.sleep(0.05)
    raw = read_all(ser, timeout=3.0, label='IRE_Init')
    if raw:
        print(f'  收到 {len(raw)} 字节')
        print(hex_dump(raw))
        echoes, responses, _ = parse_response(raw)
        if responses:
            print(f'  响应: {responses}')
            results['IRE_Init'] = True
        elif echoes:
            print(f'  仅有回显，无 RESPONSE: {echoes}')
            results['IRE_Init'] = False
        else:
            print(f'  ⚠️ 有数据但无法解析')
            results['IRE_Init'] = False
    else:
        print(f'  ⚠️ 无响应（IRE Init 可能不返回 RESPONSE）')
        results['IRE_Init'] = None  # IRE Init 可能不返回标准 RESPONSE

    time.sleep(0.5)

    # 7. 测试 IRE Window (SENDOTHER||30971,{ire},{size}) — 关键命令
    print(f'\n--- IRE Window (30971,255,10) ---')
    cmd = '\r\nSENDOTHER||30971,255,10\r\n'
    print(f'  发送: {repr(cmd)}')
    print(f'  含义: IRE=255(满白), Window=10%')
    ser.reset_input_buffer()
    written = ser.write(cmd.encode('utf-8'))
    ser.flush()
    print(f'  已写入 {written} 字节')

    time.sleep(0.05)
    raw = read_all(ser, timeout=5.0, label='IRE_Window')
    if raw:
        print(f'  收到 {len(raw)} 字节')
        print(hex_dump(raw))
        echoes, responses, _ = parse_response(raw)
        if responses:
            print(f'  响应: {responses}')
            # IRE Window 的 RESPONSE category 可能不是标准 30971+32768
            for r in responses:
                parts = r.split('||')
                if len(parts) >= 3 and parts[0] == 'RESPONSE':
                    try:
                        resp_cat = int(parts[1])
                        cmd_cat = resp_cat - 32768
                        print(f'  RESPONSE 解析: cat={cmd_cat} (resp_cat={resp_cat}), value={parts[2]}')
                    except ValueError:
                        pass
            results['IRE_Window'] = True
        elif echoes:
            print(f'  仅有回显，无 RESPONSE')
            results['IRE_Window'] = False
        else:
            results['IRE_Window'] = False
    else:
        print(f'  ❌ 无响应')
        results['IRE_Window'] = False

    time.sleep(0.3)

    # 8. 完整 IRE Window 序列测试（模拟 set_ire_window 流程）
    print(f'\n{"="*60}')
    print(f'[8] 完整 IRE Window 序列测试')
    print(f'{"="*60}')
    print(f'  模拟 set_ire_window(hdr=1, ire=255, window=10)')

    seq_cmds = [
        ('\r\nSENDSINGLE||111,1\r\n', 'HDR=HDR10', 0),
        ('\r\nSENDOTHER||63739\r\n', 'IRE Init', 0),
        ('\r\nSENDDOUBLE||98,26\r\n', 'Pattern=Window', 0),
        ('\r\nSENDOTHER||30971,255,10\r\n', 'IRE=255 Window=10%', 0.7),
    ]

    seq_results = []
    for cmd, desc, pre_delay in seq_cmds:
        if pre_delay > 0:
            print(f'\n  等待 {pre_delay}s...')
            time.sleep(pre_delay)

        print(f'\n  >> {desc}')
        print(f'     发送: {repr(cmd)}')
        ser.reset_input_buffer()
        written = ser.write(cmd.encode('utf-8'))
        ser.flush()
        print(f'     已写入 {written} 字节')

        time.sleep(0.05)
        raw = read_all(ser, timeout=3.0, label=desc)
        if raw:
            echoes, responses, full = parse_response(raw)
            if responses:
                print(f'     ✅ 响应: {responses[-1]}')
                seq_results.append(True)
            elif echoes:
                print(f'     ⚠️ 仅有回显: {echoes[-1]}')
                seq_results.append(False)
            else:
                print(f'     ⚠️ 有数据但无 RESPONSE')
                print(f'     原始: {repr(full)}')
                seq_results.append(False)
        else:
            print(f'     ❌ 无响应')
            seq_results.append(False)

        time.sleep(0.1)

    results['Full_Sequence'] = all(seq_results) if seq_results else False

    # 9. 恢复 SDR
    print(f'\n--- 恢复 HDR=SDR ---')
    test_single_command(ser, '\r\nSENDSINGLE||111,0\r\n', '恢复 SDR', expect_cat=111)

    # 关闭串口
    ser.close()
    print(f'\n串口已关闭')

    # 汇总
    print(f'\n{"="*60}')
    print(f'测试结果汇总')
    print(f'{"="*60}')
    for name, ok in results.items():
        if ok is True:
            status = '✅ 通过'
        elif ok is False:
            status = '❌ 失败'
        else:
            status = '⚠️ 无标准响应（可能正常）'
        print(f'  {name:20s} {status}')

    total = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    unknown = sum(1 for v in results.values() if v is None)
    print(f'\n  通过: {total}  失败: {failed}  无标准响应: {unknown}')

    if failed > 0:
        print(f'\n⚠️ 有命令失败，可能原因:')
        print(f'  1. 波特率不匹配（尝试其他波特率: 9600, 19200, 38400, 57600）')
        print(f'  2. 命令格式不正确（\\r\\n 包裹方式）')
        print(f'  3. 串口号错误或设备未就绪')
        print(f'  4. 设备固件版本不同，命令格式有变化')


def main():
    list_ports()

    if len(sys.argv) < 2:
        print('用法: python tools/test_murideo_serial.py <串口> [波特率]')
        print('示例: python tools/test_murideo_serial.py COM3')
        print('      python tools/test_murideo_serial.py COM3 115200')
        sys.exit(1)

    port = sys.argv[1]
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
    run_tests(port, baudrate)


if __name__ == '__main__':
    main()
