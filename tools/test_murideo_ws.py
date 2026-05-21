#!/usr/bin/env python3
"""Quick test for Murideo WebSocket connection.

Usage:
    python test_murideo_ws.py                    # default 192.168.1.239
    python test_murideo_ws.py 192.168.1.100      # custom IP
"""

import asyncio
import sys

import websockets


async def test_connection(ip: str):
    ws_url = f'ws://{ip}/ws/uart'
    print(f'连接 {ws_url} ...')

    try:
        ws = await websockets.connect(ws_url, open_timeout=5)
    except Exception as e:
        print(f'连接失败: {e}')
        return

    print('WebSocket 连接成功!')

    # Test 1: Send a known command - set pattern to White Screen (ID 11)
    cmd = '\r\nSENDDOUBLE||98,11\r\n'
    print(f'\n发送: 设置白屏图案 {repr(cmd)}')
    try:
        await ws.send(cmd)
        # Try to read response
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=3)
            print(f'响应: {repr(resp)}')
        except asyncio.TimeoutError:
            print('无响应 (超时) — 设备可能不回显')
    except Exception as e:
        print(f'发送失败: {e}')

    # Test 2: Set Window pattern (ID 26)
    await asyncio.sleep(0.5)
    cmd2 = '\r\nSENDDOUBLE||98,26\r\n'
    print(f'\n发送: 设置 Window 图案 {repr(cmd2)}')
    try:
        await ws.send(cmd2)
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=3)
            print(f'响应: {repr(resp)}')
        except asyncio.TimeoutError:
            print('无响应 (超时)')
    except Exception as e:
        print(f'发送失败: {e}')

    # Test 3: Set HDR10
    await asyncio.sleep(0.5)
    cmd3 = '\r\nSENDSINGLE||111,1\r\n'
    print(f'\n发送: 设置 HDR10 {repr(cmd3)}')
    try:
        await ws.send(cmd3)
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=3)
            print(f'响应: {repr(resp)}')
        except asyncio.TimeoutError:
            print('无响应 (超时)')
    except Exception as e:
        print(f'发送失败: {e}')

    # Test 4: Set SDR
    await asyncio.sleep(0.5)
    cmd4 = '\r\nSENDSINGLE||111,0\r\n'
    print(f'\n发送: 设置 SDR {repr(cmd4)}')
    try:
        await ws.send(cmd4)
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=3)
            print(f'响应: {repr(resp)}')
        except asyncio.TimeoutError:
            print('无响应 (超时)')
    except Exception as e:
        print(f'发送失败: {e}')

    await ws.close()
    print('\n连接已关闭')


if __name__ == '__main__':
    ip = sys.argv[1] if len(sys.argv) > 1 else '192.168.1.239'
    asyncio.run(test_connection(ip))
