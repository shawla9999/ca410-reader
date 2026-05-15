#!/usr/bin/env python3
"""Listen to Murideo WebSocket traffic.

This script connects to the Murideo WebSocket and listens for ALL messages.
While it's running, operate the Murideo Web UI in a browser (http://192.168.1.239)
to change window size and IRE/brightness — the Web UI sends commands through
the same WebSocket, so we can capture the exact command format.

Usage:
    python3 tools/sniff_murideo_ws.py 192.168.1.239

Steps:
1. Run this script
2. Open browser to http://192.168.1.239
3. In the Web UI: change window size (e.g. 10%, 20%, 50%, 100%)
4. In the Web UI: change IRE/brightness level
5. The script will print all commands it receives
6. Press Ctrl+C to stop
"""

import asyncio
import sys

import websockets

IP = sys.argv[1] if len(sys.argv) > 1 else '192.168.1.239'
WS_URL = f'ws://{IP}/ws/uart'


async def sniff():
    print(f'连接 {WS_URL} ...')
    print('请在浏览器中打开 http://192.168.1.239 并操作窗口大小/IRE')
    print('按 Ctrl+C 退出\n')

    try:
        ws = await websockets.connect(WS_URL, open_timeout=5, max_size=2**20)
    except Exception as e:
        print(f'连接失败: {e}')
        return

    print('WebSocket 连接成功! 等待消息...\n')
    print('=' * 60)

    count = 0
    try:
        async for message in ws:
            count += 1
            text = message if isinstance(message, str) else message.decode('utf-8', errors='replace')
            # Parse the command
            clean = text.strip().rstrip('\r\n')
            print(f'[{count}] {repr(clean)}')

            # Try to interpret known formats
            if '||' in clean:
                parts = clean.split('||')
                if len(parts) >= 2:
                    func = parts[0]
                    args = parts[1] if len(parts) == 2 else '||'.join(parts[1:])
                    if func == 'RESPONSE':
                        # Parse response
                        if 'error' in args.lower():
                            print(f'     -> 错误响应')
                        else:
                            resp_parts = args.split('||')
                            if len(resp_parts) >= 2:
                                try:
                                    cat = int(resp_parts[0])
                                    val = resp_parts[1]
                                    orig_cat = cat - 32768
                                    print(f'     -> 响应: Category={orig_cat}, Value={val}')
                                except ValueError:
                                    print(f'     -> 响应: {args}')
                    elif func in ('SENDSINGLE', 'SENDDOUBLE', 'SENDOTHER'):
                        arg_parts = args.split(',')
                        try:
                            cat = int(arg_parts[0])
                            vals = arg_parts[1:] if len(arg_parts) > 1 else []
                            print(f'     -> {func}: Category={cat}, Values={vals}')
                        except ValueError:
                            print(f'     -> {func}: {args}')

            print()
    except websockets.exceptions.ConnectionClosed:
        print(f'\n连接关闭 (收到 {count} 条消息)')
    except KeyboardInterrupt:
        print(f'\n用户中断 (收到 {count} 条消息)')
    finally:
        try:
            await ws.close()
        except Exception:
            pass


if __name__ == '__main__':
    asyncio.run(sniff())
