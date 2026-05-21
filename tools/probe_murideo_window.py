#!/usr/bin/env python3
"""Test IRE window size command discovered from Murideo Web UI.

Command sequence:
1. SENDDOUBLE||98,26 — Set Window pattern
2. Wait 700ms
3. SENDOTHER||30971,{size},{ire} — Set window size + IRE

Usage:
    python3 tools/probe_murideo_window.py 192.168.1.239
"""

import asyncio
import sys
import time

import websockets

IP = sys.argv[1] if len(sys.argv) > 1 else '192.168.1.239'
WS_URL = f'ws://{IP}/ws/uart'


async def send_and_recv(ws, cmd: str, label: str = '') -> str | None:
    print(f'  发送: {label or repr(cmd)}')
    try:
        await ws.send(cmd)
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=3)
            print(f'  响应: {repr(resp)}')
            return resp
        except asyncio.TimeoutError:
            print('  无响应 (超时)')
            return None
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

    # Test 1: Set Window pattern + IRE window 10%
    print('=== 测试1: 窗口10%, IRE=100 ===')
    await send_and_recv(ws, '\r\nSENDDOUBLE||98,26\r\n', 'Window pattern')
    await asyncio.sleep(0.7)
    await send_and_recv(ws, '\r\nSENDOTHER||30971,10,100\r\n', 'IRE window 10%, IRE=100')
    await asyncio.sleep(5)

    # Test 2: Set IRE window 50%
    print('\n=== 测试2: 窗口50%, IRE=100 ===')
    await send_and_recv(ws, '\r\nSENDDOUBLE||98,26\r\n', 'Window pattern')
    await asyncio.sleep(0.7)
    await send_and_recv(ws, '\r\nSENDOTHER||30971,50,100\r\n', 'IRE window 50%, IRE=100')
    await asyncio.sleep(5)

    # Test 3: Set IRE window 100%
    print('\n=== 测试3: 窗口100%, IRE=100 ===')
    await send_and_recv(ws, '\r\nSENDDOUBLE||98,26\r\n', 'Window pattern')
    await asyncio.sleep(0.7)
    await send_and_recv(ws, '\r\nSENDOTHER||30971,100,100\r\n', 'IRE window 100%, IRE=100')
    await asyncio.sleep(5)

    await ws.close()
    print('\n连接已关闭')


if __name__ == '__main__':
    asyncio.run(test())
