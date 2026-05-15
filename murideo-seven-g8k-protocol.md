# Murideo SEVEN G8K 控制协议完整参考

## 1. 控制接口概览

| 接口 | 连接方式 | 默认参数 | 备注 |
|------|----------|----------|------|
| **WebSocket** | 以太网 | `ws://192.168.1.239/ws/uart` | **首选**，协议已完整逆向 |
| **RS-232** | DB9 或 3-pin 端子 | 波特率待确认 (向 Murideo 申请) | 格式与 WebSocket 类似 |
| **USB** | USB 3.0 | 虚拟串口 | 同 RS-232 协议 |
| **Web UI** | 浏览器 | `http://192.168.1.239` | 内部走 WebSocket |

**IP 地址配置**：默认 192.168.1.239，可通过前面板 System Setup → IP Management 修改，也支持 DHCP。

**关键发现**：WebSocket 端点路径 `/ws/uart` 表明它是 UART 串口的网桥，RS-232 命令格式与 WebSocket 相同或极相似。

---

## 2. WebSocket 协议

### 2.1 连接

```
ws://{设备IP}/ws/uart
```

连接后即可发送命令和接收响应，无需认证。

### 2.2 命令格式

所有命令以 `\r\n` 包裹，使用双管道符 `||` 分隔函数和参数：

```
\r\n{FUNCTION}||{CATEGORY},{VALUE}\r\n
```

### 2.3 三种命令函数

| 函数 | 用途 | 命令类别 |
|------|------|----------|
| `SENDSINGLE` | 大部分设置命令 | 时序、色彩空间、色深、HDCP、HDR、PCM音频、系统控制等 |
| `SENDDOUBLE` | 图案和复合音频选择 | 图案选择、Dolby/DTS音频 |
| `SENDOTHER` | 特殊命令 | 恢复出厂设置 |

### 2.4 响应格式

设备返回管道分隔的文本响应。已知格式：

```
{FUNCTION}||{CATEGORY},{响应数据}
```

**时序响应示例** (设置 3840x2160 60Hz 后)：

| 字段 | 值 | 含义 |
|------|-----|------|
| Category | 32865 | 类别标识 |
| Video Clk MHz | 594 | 像素时钟 |
| H Active | 3840 | 水平有效像素 |
| V Active | 2160 | 垂直有效行 |
| H Total | 4400 | 水平总像素 |
| V Total | 2250 | 垂直总行 |
| H Blank | 560 | 水平消隐 |
| V Blank | 90 | 垂直消隐 |
| H Freq | 135 | 水平频率 kHz |
| V Freq | 60 | 垂直频率 Hz |
| Hs Width | 10 | 行同步宽度 |
| Vs Width | 88 | 场同步宽度 |
| Vs Offset | 176 | 场同步偏移 |

> 注意：响应解析在现有 GitHub 仓库中尚未完全实现，部分字段的含义仍需进一步逆向。

### 2.5 通信示例 (Python)

```python
import asyncio
import websockets

async def send_single_command(websocket, category, value):
    command = f"\r\nSENDSINGLE||{category},{value}\r\n"
    await websocket.send(command)

async def main():
    uri = "ws://192.168.1.239/ws/uart"
    async with websockets.connect(uri) as websocket:
        # 设置 3840x2160 60Hz
        await send_single_command(websocket, 97, 34)
        # 设置 100% 彩条
        await websocket.send(f"\r\nSENDDOUBLE||98,0\r\n")
        # 接收响应
        async for message in websocket:
            print("Received:", message)
            parts = message.split("||")
            if len(parts) == 3:
                command, value1, value2 = parts
                print(f"Command: {command}, V1: {value1}, V2: {value2}")

asyncio.get_event_loop().run_until_complete(main())
```

---

## 3. 完整命令 ID 字典

### 3.1 视频生成器

#### TIMING (Category: 97, SENDSINGLE)

**8K**

| ID | 名称 |
|----|------|
| 110 | 7680x4320 30Hz |
| 111 | 7680x4320 29.97Hz |
| 112 | 7680x4320 25Hz |
| 113 | 7680x4320 24Hz |
| 114 | 7680x4320 23.98Hz |
| 115 | 7680x4320 60Hz |
| 116 | 7680x4320 59.94Hz |
| 117 | 7680x4320 50Hz |
| 118 | 7680x4320 48Hz |
| 119 | 7680x4320 47.95Hz |

**UHD**

| ID | 名称 |
|----|------|
| 28 | 3840x2160 30Hz |
| 29 | 3840x2160 29.97Hz |
| 30 | 3840x2160 25Hz |
| 31 | 3840x2160 24Hz |
| 32 | 3840x2160 23.98Hz |
| 34 | 3840x2160 60Hz |
| 35 | 3840x2160 59.94Hz |
| 36 | 3840x2160 50Hz |
| 103 | 3840x2160 48Hz |
| 104 | 3840x2160 47.95Hz |
| 107 | 3840x2160 100Hz |
| 108 | 3840x2160 120Hz |
| 109 | 3840x2160 119.88Hz |

**4K-DCI**

| ID | 名称 |
|----|------|
| 53 | 4096x2160 30Hz |
| 54 | 4096x2160 29.97Hz |
| 55 | 4096x2160 25Hz |
| 44 | 4096x2160 24Hz |
| 56 | 4096x2160 23.976Hz |
| 57 | 4096x2160 60Hz |
| 58 | 4096x2160 59.94Hz |
| 59 | 4096x2160 50Hz |
| 105 | 4096x2160 48Hz |
| 106 | 4096x2160 47.95Hz |

**2K-DCI**

| ID | 名称 |
|----|------|
| 73 | 2048x1080 30Hz |
| 74 | 2048x1080 29.97Hz |
| 75 | 2048x1080 25Hz |
| 76 | 2048x1080 24Hz |
| 77 | 2048x1080 23.976Hz |
| 78 | 2048x1080 60Hz |
| 79 | 2048x1080 59.94Hz |
| 80 | 2048x1080 50Hz |

**HD**

| ID | 名称 |
|----|------|
| 12 | 720P 60Hz |
| 13 | 720P 59.94Hz |
| 14 | 1080i 60Hz |
| 15 | 1080i 59.94Hz |
| 16 | 1080p 30Hz |
| 17 | 1080p 29.97Hz |
| 18 | 1080p 24Hz |
| 19 | 1080p 23.976Hz |
| 20 | 1080p 60Hz |
| 21 | 1080p 59.94Hz |
| 24 | 720P 50Hz |
| 25 | 1080i 50Hz |
| 26 | 1080p 25Hz |
| 27 | 1080p 50Hz |
| 81 | 1080p 120Hz |
| 82 | 1080p 119.88Hz |
| 102 | 1080p 100Hz |

**SD**

| ID | 名称 |
|----|------|
| 10 | 480i 59.94Hz |
| 11 | 480p 59.94Hz |
| 22 | 576i 50Hz |
| 23 | 576p 50Hz |

**VESA**

| ID | 名称 |
|----|------|
| 0 | VGA 640x480 |
| 1 | SVGA 800x600 |
| 2 | XGA 1024x768 |
| 72 | XGA+ 1152x864 |
| 4 | HD 1360x768 |
| 3 | HD 1280x768 |
| 5 | SXGA 1280x960 |
| 7 | SXGA+ 1400x1050 |
| 69 | WXGA+ 1440x900 |
| 70 | HD+ 1600x900 |
| 8 | UXGA 1600x1200 |
| 9 | WUXGA 1920x1200 |
| 83 | XGA+ 1152x900 |
| 84 | WXGA 1280x800 |
| 85 | SXGA 1280x1050 |
| 86 | UN 1920x1280 |
| 87 | UN 1920x1440 |
| 88 | QWXGA 2048x1152 |
| 89 | QXGA 2048x1536 |
| 90 | UN 2160x1440 |
| 91 | UN 2560x1080 |
| 92 | QHD 2560x1440 |
| 93 | WQXGA 2560x1600 |
| 94 | QSXGA 2560x2048 |
| 95 | QWXGA+ 2880x1800 |
| 96 | GAL 2960x1440 |
| 97 | SUR 3000x2000 |
| 98 | WQSXGA 3200x2048 |
| 99 | UWQHD 3440x1440 |
| 101 | WQUXGA 3840x2400 |

**3D**

| ID | 名称 |
|----|------|
| 37 | 720P 60Hz (3D-FP) |
| 38 | 720P 59.94Hz (3D-FP) |
| 39 | 1080P 24Hz (3D-FP) |
| 40 | 1080P 23.976Hz (3D-FP) |
| 41 | 720P 50Hz (3D-FP) |

**CUSTOM**

| ID | 名称 |
|----|------|
| 43 | USER-1 |
| 44 | USER-2 |
| 45 | USER-3 |
| 46 | USER-4 |
| 47 | USER-5 |
| 48 | USER-6 |
| 49 | USER-9 |
| 50 | USER-8 |
| 51 | USER-9 |
| 52 | USER-10 |

**AUTO**

| ID | 名称 |
|----|------|
| 43 | Auto (基于 EDID) |

---

#### PATTERN (Category: 98, SENDDOUBLE)

**FPGA**

| ID | 名称 |
|----|------|
| 0 | 100% Color Bars |
| 1 | 75% Color Bars |
| 2 | 8 Step Gray Bars |
| 3 | 16 Step Gray Bars |
| 4 | Red Screen |
| 5 | Green Screen |
| 6 | Blue Screen |
| 7 | Cyan Screen |
| 8 | Magenta Screen |
| 9 | Yellow Screen |
| 10 | Black Screen |
| 11 | White Screen |
| 12 | Vertical Split |
| 13 | Horizontal Split |
| 14 | Multiburst Vert. |
| 15 | Multiburst Hor. |
| 16 | Quarter Block 1 |
| 17 | Quarter Block 2 |
| 18 | Alternate W.B |
| 19 | RGB CMY Ramps |
| 20 | Black Pluge |
| 21 | White Pluge |
| 22 | Still Gray Ramp 1 |
| 23 | Still Gray Ramp 2 |
| 24 | Smpte Bars |
| 25 | Border Lines |
| 26 | Window |
| 27 | 3D Boxes |
| 28 | Line V.Scroll |
| 29 | Line H.Scroll |
| 30 | A/V Sync |
| 31 | Gray Ramp |
| 32 | Red Ramp |
| 33 | Green Ramp |
| 34 | Blue Ramp |
| 35 | Moving Ball |

**ISF**

| ID | 名称 |
|----|------|
| 36 | White Pluge UHD |
| 37 | Black Pluge UHD |
| 38 | Geometry UHD |
| 39 | White Pluge HD |
| 40 | Black Pluge HD |
| 41 | Geometry 178 HD |
| 42 | Geometry 240 HD |
| 43 | ISF Color Girls |
| 44 | PD Family |
| 45 | Red Blue MTB |
| 46 | Cone Gradient |
| 47 | ISF Dog |

**DVS HDR — Clipping & Color**

| ID | 名称 |
|----|------|
| 48 | Black Level 1 |
| 49 | Black Level 2 |
| 50 | White Level 1 |
| 51 | White Level 2 |
| 52 | White Level 3 |
| 53 | White 80-100 |
| 54 | HDR Mix |
| 55 | HDR Greyscale |
| 56 | HDR Red |
| 57 | HDR Green |
| 58 | HDR Blue |
| 59 | HDR Yellow |
| 60 | HDR Cyan |
| 61 | HDR Magenta |
| 62 | Multi-Cube |
| 63 | 10 Patch Mix |
| 64 | Greyscale 1000 |
| 65 | Greyscale 2000 |
| 66 | Greyscale 4000 |
| 67 | Greyscale 10000 |
| 68 | Color High |
| 69 | Color Low |
| 70 | Decoding 50% |
| 71 | Decoding 100% |
| 72 | Blue Filter 100% |
| 73 | Green Filter 100% |
| 74 | Red Filter 100% |
| 75 | Blue Filter 50% |
| 76 | Green Filter 50% |
| 77 | Red Filter 50% |
| 78 | Color Flashing |
| 79 | Dynamic Contrast |

**DVS HDR — Evaluation**

| ID | 名称 |
|----|------|
| 80 | Landscape |
| 81 | Skin Tone |
| 82 | Skin Tone |
| 83 | City Sunset |
| 84 | Oceanside |
| 85 | Pantone Skin |
| 86 | Restaurant |
| 87 | Indian Market |
| 88 | Ambient 05 Nit |
| 89 | Ambient 10 Nit |
| 90 | Ambient 15 Nit |
| 91 | Chroma Sub 100 |
| 92 | Chroma Sub 500 |
| 93 | Chroma Sub 1000 |
| 94 | Judder 24 FPS |
| 95 | Judder 60 FPS |
| 96 | M Judder 24 FPS |

**DVS HDR — Geometry & Convergence**

| ID | 名称 |
|----|------|
| 97 | Aspect Ratio 1.78 |
| 98 | Aspect Ratio 1.85 |
| 99 | Aspect Ratio 2.00 |
| 100 | Aspect Ratio 2.35 |
| 101 | Aspect Ratio 2.40 |
| 102 | Aspect Ratio All |
| 103-109 | Grid (White/Red/Green/Blue/Yellow/Cyan/Magenta) |
| 110-116 | Dot (White/Red/Green/Blue/Yellow/Cyan/Magenta) |
| 117-123 | Cross (White/Red/Green/Blue/Yellow/Cyan/Magenta) |

**DVS HDR — Ramps, Gradients, Zone Plates**

| ID | 名称 |
|----|------|
| 124 | Greyscale Steps |
| 125 | Greyscale Ramp |
| 126 | Greyscale Mix |
| 127 | Color Steps |
| 128 | Color Ramp |
| 129 | Color Ramp H&V |
| 130 | Color Ramp Mix |
| 131 | Color Bar Ramp |
| 132-137 | Ramp (Red/Green/Blue/Yellow/Cyan/Magenta) |
| 138-144 | Zone (White/Red/Green/Blue/Magenta/Yellow/Cyan) |
| 145-151 | Radial (Grey/Red/Green/Blue/Yellow/Cyan/Magenta) |

**DVS HDR — Resolution, ANSI, Placement**

| ID | 名称 |
|----|------|
| 152 | Resolution Mix |
| 153 | Checkerboard |
| 154-156 | Horizontal 1px/2px/3px |
| 157-159 | Vertical 1px/2px/3px |
| 160 | Black Pixels |
| 161 | ANSI Meter 8x8 |
| 162 | ANSI 8x8 |
| 163 | ANSI Meter 5x4 |
| 164 | ANSI M5x4 Black |
| 165 | ANSI M5x4 White |
| 166 | Meter Placement |
| 167 | Sharp & Scan |

**DVS Dolby Vision — Clipping & Color**

| ID | 名称 |
|----|------|
| 472 | Black Level 1 |
| 473 | Black Level 2 |
| 474 | White Level 1 |
| 475 | White Level 2 |
| 476 | White Level 3 |
| 477 | White 80-100 |
| 478 | Blue Filter 50% |
| 479 | Green Filter 50% |
| 480 | Red Filter 50% |
| 481 | Color Clipping High |
| 482 | Color Clipping Low |
| 483 | Color Decoding |
| 484 | Color Flashing |

**DVS Dolby Vision — Evaluation**

| ID | 名称 |
|----|------|
| 485 | Landscape |
| 486 | Nature |
| 487 | Skin Tone |
| 488 | City Sunset |
| 489 | Oceanside |
| 490 | Pantone Skin |
| 491 | Restaurant |
| 492 | Indian Market |

**DVS Dolby Vision — Ramps, Gradients, Zone Plates**

| ID | 名称 |
|----|------|
| 493 | Greyscale Steps |
| 494 | Greyscale Ramp |
| 495 | Greyscale Mix |
| 496 | Color Steps |
| 497-502 | Radial Gradient (Red/Green/Blue/Yellow/Cyan/Magenta) |

**DVS Dolby Vision — Resolution, ANSI, Placement**

| ID | 名称 |
|----|------|
| 503 | ANSI Meter 8x8 |
| 504 | ANSI 8x8 Black |
| 505 | ANSI 8x8 White |
| 506 | ANSI Meter 5x4 |
| 507 | ANSI M5x4 Black |
| 508 | ANSI M5x4 White |
| 509 | Meter Placement |
| 510 | Sharp & Scan |

**DVS HLG — Clipping & Color**

| ID | 名称 |
|----|------|
| 511 | Black Level 1 |
| 512 | Black Level 2 |
| 513 | White Level 1 |
| 514 | White Level 2 |
| 515 | White Level 3 |
| 516 | Color Flashing |
| 517 | HDR Mix |
| 518 | HDR Greyscale |
| 519-524 | HDR (Red/Green/Blue/Yellow/Cyan/Magenta) |
| 525 | Multi-Cube |
| 526 | 10 Patch Mix |
| 527 | Color Clipping High |
| 528 | Color Clipping Low |
| 529-531 | Filter 100% (Blue/Green/Red) |
| 532 | Color Decoding 50% |
| 533 | Color Decoding 100% |

**DVS HLG — Evaluation**

| ID | 名称 |
|----|------|
| 534 | Landscape |
| 535 | Nature |
| 536 | Skin Tone |
| 537 | City Sunset |
| 538 | Oceanside |
| 539 | Pantone Skin |
| 540 | Restaurant |
| 541 | Indian Market |

**DVS HLG — Ramps, Gradients, Zone Plates**

| ID | 名称 |
|----|------|
| 542-549 | Greyscale/Color Steps/Ramps |
| 550-555 | Ramp (Red/Green/Blue/Yellow/Cyan/Magenta) |
| 556-562 | Zone (White/Red/Green/Blue/Magenta/Yellow/Cyan) |
| 563-569 | Radial (Grey/Red/Green/Blue/Yellow/Cyan/Magenta) |

**DVS HLG — Resolution, ANSI, Placement**

| ID | 名称 |
|----|------|
| 570 | ANSI Meter 8x8 |
| 571 | ANSI 8x8 Black |
| 572 | ANSI 8x8 White |
| 573 | ANSI Meter 5x4 |
| 574 | ANSI M5x4 Black |
| 575 | ANSI M5x4 White |
| 576 | Meter Placement |
| 577 | Sharp & Scan |
| 578 | Resolution Mix |

**UHD SDR — Clipping & Gamma**

| ID | 名称 |
|----|------|
| 168 | Target Limited |
| 169 | Target Full |
| 170 | Contrast Check |
| 171 | Contrast Lines |
| 172 | Gamma Check |
| 173 | Gamma Lines |
| 174 | High Clipping |
| 175-177 | High Clip (Red/Green/Blue) |
| 178 | Low Clipping |
| 179-181 | Low Clip (Red/Green/Blue) |
| 182-185 | Composite (Grey/Red/Green/Blue) |
| 186-192 | Lin Step (Grey/Red/Green/Blue/Magenta/Yellow/Cyan) |
| 193-199 | Log Step (Grey/Red/Green/Blue/Magenta/Yellow/Cyan) |
| 200-203 | Gamma (Grey/Red/Green/Blue) |
| 204-207 | Gamma Lines (Grey/Red/Green/Blue) |

**UHD SDR — Color Bars & Noise**

| ID | 名称 |
|----|------|
| 208 | Color Wipe Full |
| 209 | Color Wipe Half |
| 210 | Quick Check |
| 211 | H Bars RGB |
| 212 | H Bars RGBCMY |
| 214 | H Bars Shade |
| 215 | V Bars RGB |
| 216 | V Bars RGBCMY |
| 217 | V Bars Layover |
| 218 | V Bars Shade |
| 219-228 | Color Noise 01-16 |

**UHD SDR — Color Checker**

| ID | 名称 |
|----|------|
| 229-240 | HSL (BlueMagenta/Blue/CyanBlue/Cyan/GreenCyan/Green/MagentaRed/Magenta/Red/YellowGreen/YellowRed/Yellow) |
| 241-252 | HSV (同上，缺 BlueMagenta) |
| 253-264 | RGB (Blue/Green/Red × 064/127/191/255) |

**UHD SDR — Geometry and Resolution**

| ID | 名称 |
|----|------|
| 265-266 | Convergence (H/V) |
| 267-268 | Length (H/V) |
| 269 | Overscan |
| 270-271 | BW Evaluation |
| 272 | H Wedge |
| 273 | Star Burst |
| 274 | V Wedge |
| 275-276 | Multiburst (H/V) |
| 277-282 | Checkers (02/04/08/16/32/Log) |
| 283-284 | Circles (Many/Center) |
| 285-286 | Squares/Grid |
| 287-294 | Lines (H/V × 02/04/08/Log) |
| 295-304 | Points/Squares (02/04/08/16/32) |

**UHD SDR — Ramps**

| ID | 名称 |
|----|------|
| 305 | Color Patch |
| 306 | Triangle |
| 307 | Wireframe |
| 308-313 | Full (Red/Green/Blue/Magenta/Yellow/Cyan) |
| 314 | Full Grey |
| 315-320 | Half (Red/Green/Blue/Magenta/Yellow/Cyan) |
| 321-347 | HSL/HSV/RGB 色阶 |

**Dolby Vision**

| ID | 名称 |
|----|------|
| 425 | Dolby Vision UHD |
| 426 | CornerBox_UHD |
| 427 | Checker_UHD |
| 428-430 | Steps_UHD (L255rm1/rm2/noL255) |
| 431-433 | Ramp_UHD (L255rm1/rm2/noL255) |
| 434 | Dolby Vision FHD |
| 435 | CornerBox_FHD |
| 436 | Checker_FHD |
| 437-439 | Steps_FHD (L255rm1/rm2/noL255) |
| 440-442 | Ramp_FHD (L255rm1/rm2/noL255) |

**HD**

| ID | 名称 |
|----|------|
| 350 | High Clipping |
| 351 | Low Clipping |
| 352-355 | Color Noise (01/02/04/08) |
| 356 | Triangle |
| 357-358 | Color Wipe (Full/Half) |
| 359 | Composite |
| 360-361 | Multiburst (H/V) |
| 362-367 | Checkers (02/04/08/16/32/Log) |
| 368-370 | Circles/Squares |
| 371 | Grid |
| 372-378 | Lines (H/V) |
| 380-388 | Points/Squares |
| 389-393 | Length/Overscan/BW Evaluation/Wedge/Star Burst |
| 394-396 | H Wedge/Star Burst/V Wedge |
| 397 | RGB Text |

**PVA**

| ID | 名称 |
|----|------|
| 443-451 | BT709 (White/Black/APL_Clipping/Color_Clipping/Sharpness/Alignment/Multi_Skin/Restaurant/Skin_Tone) |
| 579-587 | BT2020 (同上) |

**SPE**

| ID | 名称 |
|----|------|
| 452-454 | 4:2:0 (Girl/Women/Girl HDR&SDR) |
| 455 | 4:4:4 Full Girl |
| 588-589 | 4:4:4 Full (Women/Girl HDR&SDR) |
| 590-591 | 4:4:4 Limit (Girl/Women) |

**Spears & Munsil**

| ID | 名称 |
|----|------|
| 456-457 | Bias Light (10%/15%) |
| 458 | Framing |
| 459-461 | Hammock (24p/30p/260i) |
| 462-463 | Mixed Video (H/V 60i) |
| 464-466 | ColorTint (Red/Green/Blue) |
| 467 | Jaggies Full 60i |
| 468-470 | Ship (1/2/3 60i) |

**User Stills**

| ID | 名称 |
|----|------|
| 398-403 | User Pattern 1-6 |

**Pattern Shortcuts**

| ID | 名称 |
|----|------|
| 471-484 | Shortcuts 1-14 |

---

#### COLOR SPACE (Category: 99, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | RGB(0-255) |
| 1 | RGB(16-235) |
| 2 | YC 4:4:4(16-235) |
| 3 | YC 4:2:2(16-235) |
| 4 | YC 4:2:0(16-235) |

#### BT 2020 (Category: 112, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | Disable |
| 1 | Enable |

#### COLOR DEPTH (Category: 100, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | 8Bit |
| 1 | 10Bit |
| 2 | 12Bit |
| 3 | 16Bit |

#### HDCP (Category: 101, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | HDCP OFF |
| 1 | HDCP 1.4 |
| 2 | HDCP 2.2 |
| 3 | HDCP AUTO |

#### HDMI/DVI (Category: 102, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | DVI |
| 1 | HDMI |
| 2 | AUTO |

#### HDR (Category: 111, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | HDR OFF (SDR) |
| 1 | HDR-10 |
| 2 | HLG |
| 3-10 | HDR CUSTOM 1-8 |

---

### 3.2 视频测试 (Category: 98, SENDDOUBLE)

| ID | 名称 |
|----|------|
| 404-408 | Spicey Pixels Chongqing (Day/Night/Lights/Cars/Cars2) |
| 409-410 | User Video Clip 1-2 |
| 411-415 | Spicey Pixels London (Yogurt/River/Sidewalk/Busses/Cafe) |
| 416-417 | Spicey Pixels Mukilteo (Street/Loading) |
| 418-421 | Spicey Pixels Carnival (Wheel/Ride/Night/Balloon Pop) |
| 422 | Spicey Pixels Tiger Mountain 120 |
| 423 | Spicey Pixels Biker 120 |
| 424 | SPE Test Video |
| 471 | Automation Testing Clip |

---

### 3.3 音频生成器

#### PCM — Sampling Rate (Category: 103, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | 32K |
| 1 | 44.1K |
| 2 | 48K |
| 3 | 88K |
| 4 | 96K |
| 5 | 176K |
| 6 | 192K |

#### PCM — Bit Depth (Category: 104, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | 16Bit |
| 1 | 20Bit |
| 2 | 24Bit |

#### PCM — Sinewave Tone (Category: 115, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | 100Hz |
| 1 | 200Hz |
| 2 | 300Hz |
| 3 | 400Hz |
| 4 | 500Hz |
| 5 | 600Hz |
| 6 | 700Hz |
| 7 | 800Hz |
| 8 | 900Hz |
| 9 | 1KHz |
| 10 | 2KHz |
| 11 | 3KHz |
| 12 | 4KHz |
| 13 | 5KHz |

#### PCM — Volume (Category: 109, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | -60dB |
| 1 | -54dB |
| 2 | -48dB |
| 3 | -42dB |
| 4 | -36dB |
| 5 | -30dB |
| 6 | -24dB |
| 7 | -18dB |
| 8 | -12dB |
| 9 | -6dB |
| 10 | 0dB |

#### PCM — Channel Config (Category: 107, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | 2CH (FR_FL) |
| 1 | 2.1CH (LFE_FR_FL) |
| 2 | 3CH (FC_FR_FL) |
| 3 | 3.1CH (FC_LFE_FR_FL) |
| 4 | 3CH (RC_FR_FL) |
| 5 | 3.1CH (RC_LFE_FR_FL) |
| 6 | 4CH (RC_LFE_FR_FL) |
| 7 | 4.1CH (RC_FC_LFE_FR_FL) |
| 8 | 4CH (RR_RL_FR_FL) |
| 9 | 4.1CH (RR_RL_LFE_FR_FL) |
| 10 | 5CH (RR_RS_FC_FR_FL) |
| 11 | 5.1CH (RR_RL_FC_LFE_FR_FL) |
| 12 | 5CH (RC_RR_RL_FR_FL) |
| 13 | 5.1CH (RC_RR_RL_LFE_FR_FL) |
| 14 | 6CH (RC_RR_RL_FC_FR_FL) |
| 15 | 6.1CH (RC_RR_RL_FC_LFE_FR_FL) |
| 16 | 6CH (RRC_RLC_RR_RL_FR_FL) |
| 17 | 6.1CH (RRC_RLC_RR_RL_LFE_FR_FL) |
| 18 | 7CH (RRC_RLC_RR_RL_FC_FR_FL) |
| 19 | 7.1CH (RRC_RLC_RR_RL_FC_LFE_FR_FL) |
| 20 | 4CH (FRC_FLC_FR_FL) |
| 21 | 4.1CH (FRC_FLC_LFE_FR_FL) |
| 22 | 5CH (FRC_FLC_FC_FR_FL) |
| 23 | 5.1CH (FRC_FLC_FC_LFE_FR_FL) |
| 24 | 5CH (FRC_FLC_RC_FR_FL) |
| 25 | 5.1CH (FRC_FLC_RC_FC_FR_FL) |
| 26 | 6CH (FRC_FLC_RC_FC_FR_FL) |
| 27 | 6.1CH (FRC_FLC_RC_FC_LFE_FR_FL) |
| 28 | 6CH (FRC_FLC_RR_RL_FR_FL) |
| 29 | 6.1CH (FRC_FLC_RR_RL_LFE_FR_FL) |
| 30 | 7CH (FRC_FLC_RR_RL_FC_FR_FL) |
| 31 | 7.1CH (FRC_FLC_RR_RL_FC_LFE_FR_FL) |

#### Dolby Audio (Category: 105, SENDDOUBLE)

**Dolby Digital**

| ID | 名称 |
|----|------|
| 2 | Dolby Digital-32KHz-2.0Ch |
| 3 | Dolby Digital-32KHz-5.1Ch |
| 4 | Dolby Digital-44.1KHz-2.0Ch |
| 5 | Dolby Digital-44.1KHz-5.1Ch |
| 6 | Dolby Digital-48KHz-2.0Ch |
| 7 | Dolby Digital-48KHz-5.1Ch |

**Dolby Digital Plus**

| ID | 名称 |
|----|------|
| 8 | Dolby Digital Plus-48KHz-2.0Ch |
| 9 | Dolby Digital Plus-48KHz-5.1Ch |
| 10 | Dolby Digital Plus-48KHz-7.1Ch |
| 11 | Dolby Digital Plus-48KHz-Atmos |

**Dolby MAT (PCM)**

| ID | 名称 |
|----|------|
| 12 | Dolby MAT(PCM)-44.1KHz-2.0Ch |
| 13 | Dolby MAT(PCM)-44.1KHz-5.1Ch |
| 14 | Dolby MAT(PCM)-44.1KHz-7.1Ch |
| 15 | Dolby MAT(PCM)-48KHz-2.0Ch |
| 16 | Dolby MAT(PCM)-48KHz-5.1Ch |
| 17 | Dolby MAT(PCM)-48KHz-7.1Ch |
| 18 | Dolby MAT(PCM object audio)-44.1KHz-Dolby Atmos |
| 19 | Dolby MAT(PCM object audio)-48KHz-Dolby Atmos |

**Dolby MAT (Dolby TrueHD)**

| ID | 名称 |
|----|------|
| 20 | Dolby MAT(Dolby TrueHD)-48KHz-2.0Ch |
| 21 | Dolby MAT(Dolby TrueHD)-48KHz-5.1Ch |
| 22 | Dolby MAT(Dolby TrueHD)-48KHz-7.1Ch |
| 23 | Dolby MAT(Dolby TrueHD)-96KHz-2.0Ch |
| 24 | Dolby MAT(Dolby TrueHD)-96KHz-5.1Ch |
| 25 | Dolby MAT(Dolby TrueHD)-96KHz-7.1Ch |
| 26 | Dolby MAT(Dolby TrueHD)-192KHz-2.0Ch |
| 27 | Dolby MAT(Dolby TrueHD)-192KHz-5.1Ch |
| 28 | Dolby MAT(Dolby TrueHD) Object Based 48KHz-Dolby Atmos |

**Dolby My Streams**

| ID | 名称 |
|----|------|
| 288 | MY STREAM1 |
| 308 | MY STREAM2 |
| 328 | MY STREAM3 |
| 348 | MY STREAM4 |
| 368 | MY STREAM5 |
| 388 | MY STREAM6 |

#### External Analog L/R (Category: 105, SENDDOUBLE)

| ID | 名称 |
|----|------|
| 0 | ENABLE |

#### DTS Audio (Category: 105, SENDDOUBLE)

**DTS Digital Surround**

| ID | 名称 |
|----|------|
| 562 | DTS Digital Surround-48KHz-2.0Ch |
| 563 | DTS Digital Surround-48KHz-5.1Ch |
| 564 | DTS Digital Surround-48.1KHz-6.1Ch |
| 565 | DTS Digital Surround-44.1KHz-5.1Ch |
| 566 | DTS Digital Surround-96KHz-5.1Ch |

**DTS-HD High Resolution**

| ID | 名称 |
|----|------|
| 567 | DTS-HD High Resolution-48KHz-5.1Ch |
| 568 | DTS-HD High Resolution-48KHz-7.1Ch |
| 569 | DTS-HD High Resolution-96KHz-7.1Ch |
| 570 | DTS-HD High Resolution-88.2KHz-7.1Ch |

**DTS-HD Master Audio**

| ID | 名称 |
|----|------|
| 571 | DTS-HD Master Audio-48KHz-5.1Ch |
| 572 | DTS-HD Master Audio-48KHz-7.1Ch |
| 573 | DTS-HD Master Audio-192KHz-2.0Ch |
| 574 | DTS-HD Master Audio-192KHz-7.1Ch |

**DTS:X**

| ID | 名称 |
|----|------|
| 575 | DTS:X-48KHz-7.1.4Ch |
| 576 | DTS:X-48KHz-5.1.4Ch |
| 577 | DTS:X Master Audio-48KHz-7.1.4Ch |
| 578 | DTS:X Master Audio-96KHz-7.1.4Ch |
| 579 | DTS:X(32 Objects) |

**DTS Express**

| ID | 名称 |
|----|------|
| 580 | DTS Low Bit Rate-48KHz-5.1Ch |

**DTS My Streams**

| ID | 名称 |
|----|------|
| 581 | MY STREAM1 |
| 601 | MY STREAM2 |
| 621 | MY STREAM3 |
| 641 | MY STREAM4 |
| 661 | MY STREAM5 |
| 681 | MY STREAM6 |

---

### 3.4 音频测试

#### Sync-Latency Test — Video Settings

| ID | 名称 |
|----|------|
| 0 | 3840x2160 30Hz |
| 1 | 3840x2160 29.97Hz |
| 2 | 3840x2160 25Hz |
| 3 | 3840x2160 24Hz |
| 4 | 3840x2160 60Hz |
| 5 | 3840x2160 59.94Hz |
| 6 | 3840x2160 50Hz |
| 7 | 1080P 30Hz |
| 8 | 1080P 29.97Hz |
| 9 | 1080P 25Hz |
| 10 | 1080P 24Hz |
| 11 | 1080P 60Hz |
| 12 | 1080P 59.94Hz |
| 13 | 1080P 50Hz |
| 14 | 1080P 120Hz |
| 15 | 1080P 119.88Hz |

#### Dolby Vision Settings

| ID | 名称 |
|----|------|
| 0 | DOLBY VISION OFF |
| 1 | DOLBY VISION SINK-LED |
| 2 | DOLBY VISION SOURCE-LED |

#### AV Sensors Functional Test

| ID | 名称 |
|----|------|
| 0 | Mic Functional Test - READ STATUS |
| 1 | Visual Sensor Test - READ STATUS |

#### Source-Speaker Test

| ID | 名称 |
|----|------|
| 528 | SPEAKER ALLOCATION |
| 538 | WHITE NOISE |
| 548 | SWEEP AUDIO |

---

### 3.5 EDID / eARC / CDS

#### Sink Device EDID Info

| ID | 名称 |
|----|------|
| 1 | READ EDID |

#### ARC HPD CTL

| ID | 名称 |
|----|------|
| 0 | DEASSERT HPD (LOW) |
| 1 | ASSERT HPD (HIGH) |

#### ARC Physical HPD CTL (Category: 177, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | DEASSERT HPD (LOW) |
| 1 | ASSERT HPD (HIGH) |

#### eARC HPD bit CTL (Category: 178, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | CLEAR HDMI_HPD bit (=0) |
| 1 | SET HDMI_HPD bit (=1) |

#### HDMI +5V Power CTL (Category: 179, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | SET HDMI TX +5V OFF |
| 1 | SET HDMI TX +5V ON |

#### CEC Command (Category: 122, SENDSINGLE)

发送 CEC 命令，参数为十六进制字符串，如 `"05.0E.3A.63"`。

---

### 3.6 系统设置

#### ARC/eARC OUT SETUP (Category: 131, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | Disable ARC/eARC |
| 1 | Enable eARC |
| 2 | Enable ARC |

#### Fan Control (Category: 30723, SENDSINGLE)

| ID | 名称 |
|----|------|
| 0 | OFF |
| 1 | LOW SPEED |
| 2 | MIDDLE SPEED |
| 3 | HIGH SPEED |

#### Factory Reset (Category: 30722, SENDOTHER)

```
\r\nSENDOTHER||30722\r\n
```

#### Vitals (Category: 1, SENDSINGLE)

读取设备信息（固件版本、芯片温度等）。

#### eARC TX Latency (Category: 121, SENDSINGLE)

参数为延迟毫秒值。

#### eARC RX Latency (Category: 122, SENDSINGLE)

参数为延迟毫秒值。

---

## 4. 命令速查表

| 功能 | Category | 函数 | 示例 |
|------|----------|------|------|
| 设置时序 | 97 | SENDSINGLE | `\r\nSENDSINGLE\|\|97,34\r\n` |
| 选择图案 | 98 | SENDDOUBLE | `\r\nSENDDOUBLE\|\|98,0\r\n` |
| 色彩空间 | 99 | SENDSINGLE | `\r\nSENDSINGLE\|\|99,0\r\n` |
| 色深 | 100 | SENDSINGLE | `\r\nSENDSINGLE\|\|100,1\r\n` |
| HDCP | 101 | SENDSINGLE | `\r\nSENDSINGLE\|\|101,2\r\n` |
| HDMI/DVI | 102 | SENDSINGLE | `\r\nSENDSINGLE\|\|102,1\r\n` |
| PCM采样率 | 103 | SENDSINGLE | `\r\nSENDSINGLE\|\|103,2\r\n` |
| PCM位深 | 104 | SENDSINGLE | `\r\nSENDSINGLE\|\|104,2\r\n` |
| Dolby/DTS | 105 | SENDDOUBLE | `\r\nSENDDOUBLE\|\|105,11\r\n` |
| PCM声道 | 107 | SENDSINGLE | `\r\nSENDSINGLE\|\|107,11\r\n` |
| PCM音量 | 109 | SENDSINGLE | `\r\nSENDSINGLE\|\|109,10\r\n` |
| HDR | 111 | SENDSINGLE | `\r\nSENDSINGLE\|\|111,1\r\n` |
| BT.2020 | 112 | SENDSINGLE | `\r\nSENDSINGLE\|\|112,1\r\n` |
| PCM正弦波 | 115 | SENDSINGLE | `\r\nSENDSINGLE\|\|115,9\r\n` |
| ARC/eARC | 131 | SENDSINGLE | `\r\nSENDSINGLE\|\|131,1\r\n` |
| eARC TX延迟 | 121 | SENDSINGLE | `\r\nSENDSINGLE\|\|121,100\r\n` |
| CEC命令 | 122 | SENDSINGLE | `\r\nSENDSINGLE\|\|122,05.0E.3A.63\r\n` |
| ARC HPD | 177 | SENDSINGLE | `\r\nSENDSINGLE\|\|177,1\r\n` |
| eARC HPD | 178 | SENDSINGLE | `\r\nSENDSINGLE\|\|178,1\r\n` |
| HDMI +5V | 179 | SENDSINGLE | `\r\nSENDSINGLE\|\|179,1\r\n` |
| 恢复出厂 | 30722 | SENDOTHER | `\r\nSENDOTHER\|\|30722\r\n` |
| 风扇控制 | 30723 | SENDSINGLE | `\r\nSENDSINGLE\|\|30723,2\r\n` |

---

## 5. 已知限制和注意事项

1. **响应解析不完整**：现有 GitHub 仓库的响应解析是 TODO 状态，部分响应字段含义不明
2. **RS-232 串口参数未知**：波特率等需要向 Murideo 申请文档确认
3. **官方 API 文档需申请**：手册标注 "API Available upon request"，联系 support@murideo.com 或致电 877-886-5112
4. **命令执行无确认**：命令发送后设备是否执行成功需通过响应或观察输出判断
5. **并发限制**：未知是否支持同时发送多个命令，建议串行发送并等待响应
6. **CEC 命令格式**：参数为点分隔的十六进制字符串，如 `05.0E.3A.63`

---

## 6. 参考资源

- **GitHub 逆向项目**：https://github.com/JFaulk1434/Murideo_8K_Seven_API
  - `dictionary_markdown.md` — 完整命令字典 (37KB)
  - `resources/map_key.py` — Python 命令字典 (87KB)
  - `resources/murideo.py` — Python WebSocket 客户端库
  - `request_test.py` — 最小化测试脚本
  - `response_cypher.md` — 响应格式说明
- **Murideo 官网**：https://www.murideo.com
- **AVPro Edge 支持门户**：https://support.avproedge.com
- **第三方控制集成**：Calman / Light Illusion 均已支持自动接口控制
