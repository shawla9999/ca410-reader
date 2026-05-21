#!/usr/bin/env python3
"""Test IRE window command with proper delays in one connection.

Confirms the parameter order and timing requirements.

Usage:
    python3 tools/test_ire_window2.py 192.168.1.239
"""

import asyncio
import sys

import websockets

IP = sys.argv[1] if len(sys.argv) > 1 else '192.168.1.239'
WS_URL = f'ws://{IP}/ws/uart'


async def test():
    print(f'连接 {WS_URL} ...')
    try:
        ws = await websockets.connect(WS_URL, open_timeout=5, max_size=2**20)
    except Exception as e:
        print(f'连接失败: {e}')
        return

    print('WebSocket 连接成功!\n')

    # All commands in one connection, with proper delays
    # Test: Window 100%, IRE=100 (should be full screen white)
    print('=== 单连接测试: IRE init + Window + IRE=100, 窗口=100% ===')

    # Step 1: IRE init
    cmd1 = '\r\nSENDOTHER||63739\r\n'
    print(f'发送: IRE init (63739)')
    await ws.send(cmd1)
    # Read all responses
    try:
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=2)
            print(f'  响应: {repr(resp.strip())}')
    except asyncio.TimeoutError:
        pass

    # Wait 2 seconds after IRE init
    print('等待 2 秒...')
    await asyncio.sleep(2)

    # Step 2: Window pattern
    cmd2 = '\r\nSENDDOUBLE||98,26\r\n'
    print(f'发送: Window pattern (98,26)')
    await ws.send(cmd2)
    try:
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=2)
            print(f'  响应: {repr(resp.strip())}')
    except asyncio.TimeoutError:
        pass

    # Wait 700ms
    await asyncio.sleep(0.7)

    # Step 3: IRE window - format: SENDOTHER||30971,{IRE},{window_size}
    # IRE=100, window_size=100
    cmd3 = '\r\nSENDOTHER||30971,100,100\r\n'
    print(f'发送: SENDOTHER||30971,100,100 (IRE=100, 窗口=100%)')
    await ws.send(cmd3)
    try:
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=2)
            print(f'  响应: {repr(resp.strip())}')
    except asyncio.TimeoutError:
        pass

    print('\n等待 5 秒观察输出...')
    await asyncio.sleep(5)

    # Now test: IRE=50, window_size=50
    print('\n=== 测试2: IRE=50, 窗口=50% ===')
    cmd4 = '\r\nSENDDOUBLE||98,26\r\n'
    print(f'发送: Window pattern')
    await ws.send(cmd4)
    try:
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=2)
            print(f'  响应: {repr(resp.strip())}')
    except asyncio.TimeoutError:
        pass

    await asyncio.sleep(0.7)

    cmd5 = '\r\nSENDOTHER||30971,50,50\r\n'
    print(f'发送: SENDOTHER||30971,50,50 (IRE=50, 窗口=50%)')
    await ws.send(cmd5)
    try:
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=2)
            print(f'  响应: {repr(resp.strip())}')
    except asyncio.TimeoutError:
        pass

    print('\n等待 5 秒观察输出...')
    await asyncio.sleep(5)

    # Test: IRE=100, window_size=10
    print('\n=== 测试3: IRE=100, 窗口=10% ===')
    cmd6 = '\r\nSENDDOUBLE||98,26\r\n'
    print(f'发送: Window pattern')
    await ws.send(cmd6)
    try:
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=2)
            print(f'  响应: {repr(resp.strip())}')
    except asyncio.TimeoutError:
        pass

    await asyncio.sleep(0.7)

    cmd7 = '\r\nSENDOTHER||30971,100,10\r\n'
    print(f'发送: SENDOTHER||30971,100,10 (IRE=100, 窗口=10%)')
    await ws.send(cmd7)
    try:
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=2)
            print(f'  响应: {repr(resp.strip())}')
    except asyncio.TimeoutError:
        pass

    print('\n等待 5 秒观察输出...')
    await asyncio.sleep(5)

    await ws.close()
    print('\n连接已关闭')


if __name__ == '__main__':
    asyncio.run(test())
