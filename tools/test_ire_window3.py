#!/usr/bin/env python3
"""Test IRE window: init only once, then change IRE/size without re-init.

Usage:
    python3 tools/test_ire_window3.py 192.168.1.239
"""

import asyncio
import sys

import websockets

IP = sys.argv[1] if len(sys.argv) > 1 else '192.168.1.239'
WS_URL = f'ws://{IP}/ws/uart'


async def drain(ws, timeout=2):
    try:
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=timeout)
            print(f'  响应: {repr(resp.strip())}')
    except asyncio.TimeoutError:
        pass


async def test():
    print(f'连接 {WS_URL} ...')
    try:
        ws = await websockets.connect(WS_URL, open_timeout=5, max_size=2**20)
    except Exception as e:
        print(f'连接失败: {e}')
        return

    print('WebSocket 连接成功!\n')

    # Step 1: IRE init (only once)
    print('=== IRE 初始化 (只发一次) ===')
    await ws.send('\r\nSENDOTHER||63739\r\n')
    await drain(ws)
    await asyncio.sleep(2)

    # Step 2: Window pattern + IRE=100, 窗口=100%
    print('\n=== 测试1: IRE=100, 窗口=100% ===')
    await ws.send('\r\nSENDDOUBLE||98,26\r\n')
    await drain(ws)
    await asyncio.sleep(0.7)
    await ws.send('\r\nSENDOTHER||30971,100,100\r\n')
    await drain(ws)
    print('等待 5 秒观察...')
    await asyncio.sleep(5)

    # Step 3: Window pattern + IRE=50, 窗口=50% (no re-init)
    print('\n=== 测试2: IRE=50, 窗口=50% (不重新初始化) ===')
    await ws.send('\r\nSENDDOUBLE||98,26\r\n')
    await drain(ws)
    await asyncio.sleep(0.7)
    await ws.send('\r\nSENDOTHER||30971,50,50\r\n')
    await drain(ws)
    print('等待 5 秒观察...')
    await asyncio.sleep(5)

    # Step 4: Window pattern + IRE=100, 窗口=10%
    print('\n=== 测试3: IRE=100, 窗口=10% (不重新初始化) ===')
    await ws.send('\r\nSENDDOUBLE||98,26\r\n')
    await drain(ws)
    await asyncio.sleep(0.7)
    await ws.send('\r\nSENDOTHER||30971,100,10\r\n')
    await drain(ws)
    print('等待 5 秒观察...')
    await asyncio.sleep(5)

    # Step 5: Window pattern + IRE=10, 窗口=20%
    print('\n=== 测试4: IRE=10, 窗口=20% (不重新初始化) ===')
    await ws.send('\r\nSENDDOUBLE||98,26\r\n')
    await drain(ws)
    await asyncio.sleep(0.7)
    await ws.send('\r\nSENDOTHER||30971,10,20\r\n')
    await drain(ws)
    print('等待 5 秒观察...')
    await asyncio.sleep(5)

    await ws.close()
    print('\n连接已关闭')


if __name__ == '__main__':
    asyncio.run(test())
