#!/usr/bin/env python3
"""Test IRE window commands with initialization.

Web UI flow:
1. Click IRE WINDOW tab -> SENDOTHER||63739 (init IRE mode)
2. Adjust sliders -> data_deal() -> emit "win_size" with [size, ire]
3. Listener sends: SENDDOUBLE||98,26 (Window pattern)
4. After 700ms: SENDOTHER||30971,{size},{ire}

Usage:
    python3 tools/test_ire_window.py 192.168.1.239
"""

import asyncio
import sys

import websockets

IP = sys.argv[1] if len(sys.argv) > 1 else '192.168.1.239'
WS_URL = f'ws://{IP}/ws/uart'


async def send_and_recv(ws, cmd: str, label: str = '', timeout: float = 3) -> str | None:
    print(f'  发送: {label or repr(cmd)}')
    try:
        await ws.send(cmd)
        # Read all available responses
        responses = []
        try:
            while True:
                resp = await asyncio.wait_for(ws.recv(), timeout=timeout)
                responses.append(resp)
                timeout = 0.5  # Shorter timeout for subsequent reads
        except asyncio.TimeoutError:
            pass
        for r in responses:
            print(f'  响应: {repr(r)}')
        return responses[0] if responses else None
    except Exception as e:
        print(f'  发送失败: {e}')
        return None


async def test():
    print(f'连接 {WS_URL} ...')
    try:
        ws = await websockets.connect(WS_URL, open_timeout=5)
    except Exception as e:
        print(f'连接失败: {e}')
        return

    print('WebSocket 连接成功!\n')

    # Step 1: Initialize IRE window mode
    print('=== 初始化 IRE WINDOW 模式 ===')
    await send_and_recv(ws, '\r\nSENDOTHER||63739\r\n', 'SENDOTHER||63739 (IRE init)', timeout=5)
    await asyncio.sleep(2)

    # Step 2: Test window 10%, IRE=100
    print('\n=== 测试1: 窗口10%, IRE=100 ===')
    await send_and_recv(ws, '\r\nSENDDOUBLE||98,26\r\n', 'Window pattern')
    await asyncio.sleep(0.7)
    await send_and_recv(ws, '\r\nSENDOTHER||30971,10,100\r\n', 'IRE window 10%, IRE=100')
    await asyncio.sleep(5)

    # Step 3: Test window 50%, IRE=100
    print('\n=== 测试2: 窗口50%, IRE=100 ===')
    await send_and_recv(ws, '\r\nSENDDOUBLE||98,26\r\n', 'Window pattern')
    await asyncio.sleep(0.7)
    await send_and_recv(ws, '\r\nSENDOTHER||30971,50,100\r\n', 'IRE window 50%, IRE=100')
    await asyncio.sleep(5)

    # Step 4: Test window 100%, IRE=100
    print('\n=== 测试3: 窗口100%, IRE=100 ===')
    await send_and_recv(ws, '\r\nSENDDOUBLE||98,26\r\n', 'Window pattern')
    await asyncio.sleep(0.7)
    await send_and_recv(ws, '\r\nSENDOTHER||30971,100,100\r\n', 'IRE window 100%, IRE=100')
    await asyncio.sleep(5)

    # Step 5: Try different value formats
    # Maybe window_size is 0-255 not 0-100?
    print('\n=== 测试4: 窗口=255 (最大), IRE=100 ===')
    await send_and_recv(ws, '\r\nSENDDOUBLE||98,26\r\n', 'Window pattern')
    await asyncio.sleep(0.7)
    await send_and_recv(ws, '\r\nSENDOTHER||30971,255,100\r\n', 'IRE window 255, IRE=100')
    await asyncio.sleep(5)

    # Step 6: Maybe IRE and size are swapped?
    print('\n=== 测试5: 参数互换 - IRE=10, size=100 ===')
    await send_and_recv(ws, '\r\nSENDDOUBLE||98,26\r\n', 'Window pattern')
    await asyncio.sleep(0.7)
    await send_and_recv(ws, '\r\nSENDOTHER||30971,100,10\r\n', 'SENDOTHER||30971,100,10')
    await asyncio.sleep(5)

    await ws.close()
    print('\n连接已关闭')


if __name__ == '__main__':
    asyncio.run(test())
