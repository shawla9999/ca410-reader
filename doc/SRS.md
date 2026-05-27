# PqReadTool 软件需求规格说明书

**文档编号**: SRS-PqReadTool-001
**版本**: 1.0
**日期**: 2026-05-22
**状态**: 发布

---

## 修订记录

| 版本 | 日期 | 修改人 | 修改说明 |
|------|------|--------|----------|
| 1.0 | 2026-05-22 | — | 初始版本 |

---

## 目录

1. [引言](#1-引言)
2. [总体描述](#2-总体描述)
3. [功能需求](#3-功能需求)
4. [非功能需求](#4-非功能需求)
5. [数据结构定义](#5-数据结构定义)
6. [约束与假设](#6-约束与假设)
7. [参考文档](#7-参考文档)

---

## 1 引言

### 1.1 编写目的

本文档定义 PqReadTool（显示画质自动测试工具）的软件需求，为系统的设计、开发、测试和验收提供依据。本文档的预期读者包括：项目经理、软件开发工程师、测试工程师、产品负责人。

### 1.2 项目背景

显示设备（电视机、显示器）的画质测试是一项高度依赖人工的重复性工作。典型测试流程如下：

1. 操作人员在 Murideo 信号发生器上设置测试图案和参数（HDR模式、IRE亮度、窗口大小等）
2. 调整电视机上的图像参数（图像模式、峰值亮度、背光值、Local Dimming等）
3. 使用 CA-410 色彩分析仪测量屏幕的亮度（Lv）和色度（x, y）
4. 将测量结果手动记录到 Excel 表格中

一次完整的峰值亮度测试通常包含数百到数千个测试用例，每个用例都需要重复上述步骤。人工操作不仅效率低下，而且容易出现遗漏和记录错误。

**项目目标**：自动化上述测试工作流，通过软件同时控制 Murideo 信号发生器和 CA-410 色彩分析仪，实现测试用例的自动加载、信号参数的自动设置、亮度和色度的自动测量，以及测量结果的自动写入 Excel，从而大幅提升测试效率和数据准确性。

### 1.3 术语与缩略语

| 术语/缩略语 | 全称 | 说明 |
|-------------|------|------|
| CA-410 | CA-410 Color Analyzer | 柯尼卡美能达色彩分析仪 |
| CA-S40 | CA-S40 Communication Protocol | CA-410 串口通信协议 |
| IRE | Institute of Radio Engineers | 亮度等级，范围 0-255，255 表示全白 |
| Lv | Luminance | 亮度，单位 cd/m² |
| xyLv | Chromaticity (x, y) + Luminance | 色度坐标 (x, y) + 亮度测量模式 |
| TduvLv | Color Temperature (Tcp) + duv + Luminance | 色温 (Tcp) + duv + 亮度测量模式 |
| HDR10 | High Dynamic Range (Mode 1) | 高动态范围 HDR 模式 |
| HLG | Hybrid Log-Gamma (Mode 2) | 混合对数伽马 HDR 模式 |
| SDR | Standard Dynamic Range | 标准动态范围 |
| BT.2020 | ITU-R BT.2020 | 宽色域标准 |
| Local Dimming | Local Dimming | 背光分区控制技术 |

---

## 2 总体描述

### 2.1 运行环境

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 桌面系统 |
| Python 版本 | Python 3.12+ |
| 核心依赖 | pyserial >= 3.5, websockets >= 12.0, openpyxl >= 3.0 |
| 打包方式 | PyInstaller 单文件 EXE（CA410Reader.spec） |
| 硬件接口 | CA-410 串口连接、Murideo 网络或串口连接 |

### 2.2 用户特征

本系统的用户为显示设备画质测试工程师，具备以下特征：

- 具备显示画质测试的基本知识（HDR/SDR、IRE、亮度/色度等）
- 能够操作 CA-410 色彩分析仪和 Murideo 信号发生器
- 能够使用 Excel 管理测试用例和结果
- 需要物理接触电视机以调整其图像设置

### 2.3 系统架构

系统采用四层模块化架构：

```
┌──────────────────────────────────────────────┐
│                  UI 层                        │
│  (MainWindow, ConnectionPanel, MeasurementPanel,│
│   MurideoPanel, ControlPanel, HistoryPanel)    │
├──────────────────────────────────────────────┤
│                Worker 层                      │
│  (MeasurementWorker, AutoTestWorker)           │
├──────────────────────────────────────────────┤
│                Driver 层                      │
│  (CA410Driver, MurideoDriver)                  │
├──────────────────────────────────────────────┤
│               Transport 层                    │
│  (Serial, WebSocketTransport, SerialTransport) │
└──────────────────────────────────────────────┘
```

- **UI 层**：基于 tkinter/ttk 的图形界面，负责用户交互和数据显示
- **Worker 层**：后台线程管理，将硬件 I/O 操作从 UI 线程中分离
- **Driver 层**：设备通信协议实现（CA-S40 协议、Murideo 命令协议）
- **Transport 层**：底层传输通道（串口、WebSocket）

### 2.4 系统外部接口

| 接口 | 类型 | 说明 |
|------|------|------|
| CA-410 | 串口 (RS-232/USB虚拟COM) | CA-S40 协议，38400/8N1 |
| Murideo | WebSocket 或串口 | WebSocket: ws://{IP}/ws/uart（首选）；串口: RS-232/USB虚拟COM，默认 115200/8N1 |
| Excel 文件 | 文件 I/O | .xlsx 格式，openpyxl 读写 |
| JSON 文件 | 文件 I/O | 测试方案配置、用户偏好设置 |

---

## 3 功能需求

### 3.1 CA-410 连接与测量

#### REQ-CA410-001 串口自动发现

**优先级**: 高
**描述**: 系统应自动扫描本机所有 COM 端口，通过端口描述（description）或制造商（manufacturer）字段中包含 "Konica"、"CA-410" 或 "CA-S40" 关键字来识别 CA-410 设备。若仅检测到一个 COM 端口，应自动选择该端口，无需用户手动指定。

**验收标准**:
1. 扫描 `serial.tools.list_ports.comports()` 返回的所有端口
2. 对每个端口的 description 和 manufacturer 字段进行大小写无关的匹配
3. 匹配关键字: "konica"、"ca-410"、"ca-s40"
4. 若仅存在一个 COM 端口，自动返回该端口
5. 若未匹配到任何端口，返回 None 并提示用户手动选择

---

#### REQ-CA410-002 连接与断开

**优先级**: 高
**描述**: 系统应支持 CA-410 的连接和断开操作。连接时按序执行以下初始化步骤；断开时退出远程模式并关闭串口。

**连接流程**:
1. 以 38400 波特率、8N1 格式打开串口（rtscts=False, dsrdtr=False）
2. 发送 `COM,1` 进入远程模式
3. 等待 500ms（设备进入远程模式需要时间）
4. 发送 `PSC,1` 选择探头 1；若返回 `ER10`（未定义命令），捕获 `UndefinedCommandError` 异常并跳过（单探头 CA-410 不支持 PSC 命令）
5. 发送 `MDS,0` 设置 xyLv 显示模式
6. 尝试发送 `ZRC` 执行零点校准；若探头盖未盖上导致失败，跳过（用户可后续手动校准）

**断开流程**:
1. 发送 `COM,0` 退出远程模式
2. 关闭串口

**验收标准**:
1. 连接成功后设备处于远程模式、xyLv 显示模式
2. 单探头设备连接不因 PSC 命令失败而中断
3. 断开后串口正确释放

---

#### REQ-CA410-003 单次测量

**优先级**: 高
**描述**: 系统应支持向 CA-410 发送 `MES` 命令触发单次测量，并解析返回的测量结果。

**ER10 自动重试机制**:
- 若 `MES` 返回 `ER10`（表示需要零点校准），系统应自动执行 `ZRC` 零点校准命令
- 校准成功后重新发送 `MES` 命令进行测量
- 若校准后仍测量失败，向用户报告错误："测量失败：请盖上探头盖执行零点校准后再测量"

**响应解析**:
- xyLv 模式响应格式: `OK00,P1 230;182;12.4`，顺序为 x; y; Lv
- TduvLv 模式响应格式: `OK00,P1 0.000;0.000;0.000`，顺序为 Lv; Tcp; duv
- 色度值 x, y 省略 "0." 前缀（如 "230" 表示 0.230）

**验收标准**:
1. 正确解析 xyLv 和 TduvLv 两种模式的测量响应
2. ER10 自动重试机制正确触发
3. 色度值 "0." 前缀缺失情况正确处理

---

#### REQ-CA410-004 连续测量

**优先级**: 中
**描述**: 系统应支持以可配置的时间间隔（默认 1.0 秒）重复执行 CA-410 测量，直到用户主动停止或连接断开。

**验收标准**:
1. 连续测量在后台线程中运行，不影响 UI 响应
2. 每次测量间隔可配置
3. 用户可随时停止连续测量
4. 连接断开时自动停止

---

#### REQ-CA410-005 零点校准

**优先级**: 高
**描述**: 系统应支持手动触发零点校准（ZRC 命令）。校准前须确保探头盖已盖上且无环境光照射。

**验收标准**:
1. 发送 ZRC 命令执行零点校准
2. 校准成功后通知用户
3. 校准失败时给出中文错误提示

---

#### REQ-CA410-006 测量模式切换

**优先级**: 中
**描述**: 系统应支持在运行时切换测量显示模式，包括 xyLv 模式（模式 0，返回 Lv, x, y）和 TduvLv 模式（模式 2，返回 Lv, Tcp, duv）。

**验收标准**:
1. 通过 `MDS,{mode}` 命令切换模式
2. 切换后测量结果按新模式的格式解析
3. 若当前已处于目标模式，不重复发送命令

---

### 3.2 Murideo 信号发生器控制

#### REQ-MUR-001 双通道连接

**优先级**: 高
**描述**: 系统应支持两种传输方式连接 Murideo Seven G8K 信号发生器：WebSocket（首选）和串口（RS-232/USB虚拟COM）。连接时应验证设备响应，并检测是否误连接了其他设备（如 CA-410）。

**WebSocket 连接**:
- 连接地址: `ws://{IP}/ws/uart`
- 持久连接，后台线程维护
- 心跳保活: 每 30 秒发送 ping，60 秒超时
- 自动重连: 最多 3 次，指数退避（1s, 2s, 4s）

**串口连接**:
- 默认波特率: 115200，8N1 格式，用户可配置
- 连接后发送 `SENDSINGLE||111,0` 进行握手验证
- 若响应包含 `RESPONSE`，握手成功
- 若响应以 `ER` 开头，判定为连接了错误设备（如 CA-410），给出提示："串口连接的似乎不是 Murideo（收到 ERxx），请确认串口是否连接了 CA-410 色彩分析仪"
- 若无响应，提示检查波特率和连接状态

**验收标准**:
1. WebSocket 和串口两种传输方式均可正常连接和断开
2. 连接时验证设备响应
3. 误连接 CA-410 到 Murideo 串口时正确识别并提示
4. WebSocket 断线后自动重连

---

#### REQ-MUR-002 HDR/SDR 模式设置

**优先级**: 高
**描述**: 系统应支持设置 Murideo 的 HDR/SDR 模式，包括 SDR（模式 0）、HDR10（模式 1）和 HLG（模式 2）。

**命令格式**: `SENDSINGLE||111,{mode}`

**验收标准**:
1. 正确发送 HDR 模式命令
2. 支持三种模式：SDR=0, HDR10=1, HLG=2

---

#### REQ-MUR-003 IRE 亮度与窗口大小控制

**优先级**: 高
**描述**: 系统应支持设置 IRE 亮度等级（0-255）和窗口大小（0-100%）。IRE/窗口参数通过以下命令序列设置：

1. 发送 `SENDOTHER||63739` 初始化 IRE 模式
2. 发送 `SENDDOUBLE||98,26` 选择 Window 图案
3. 等待 700ms
4. 发送 `SENDOTHER||30971,{IRE},{SIZE}`

同时支持可选的附加参数同步设置：timing（信号格式）、color_space（色彩空间）、color_depth（色深）、hdr（HDR模式）、bt2020（BT.2020）、pattern（测试图案）。这些参数在 IRE 初始化之前按序发送。

**验收标准**:
1. IRE 和窗口大小正确设置
2. 700ms 延迟在图案选择和 IRE 值命令之间严格执行
3. 附加参数可选且按正确顺序发送
4. IRE 值范围限制在 0-255，窗口大小限制在 0-100

---

#### REQ-MUR-004 信号格式/色彩空间/色深/图案设置

**优先级**: 中
**描述**: 系统应支持独立设置以下 Murideo 参数：

| 参数 | 命令类别 | 命令格式 | 可选值 |
|------|---------|---------|--------|
| 信号格式 (Timing) | 97 | `SENDSINGLE\|97,{id}` | 34=3840x2160@60Hz, 20=1080p@60Hz 等 |
| 色彩空间 (Color Space) | 99 | `SENDSINGLE\|99,{val}` | 0=RGB(0-255), 1=RGB(16-235), 2=YC444, 3=YC422, 4=YC420 |
| 色深 (Color Depth) | 100 | `SENDSINGLE\|100,{val}` | 0=8bit, 1=10bit, 2=12bit, 3=16bit |
| 测试图案 (Pattern) | 98 | `SENDDOUBLE\|98,{id}` | 0=ColorBars, 10=Black, 11=White, 26=Window 等 |

**验收标准**:
1. 各参数可独立设置
2. 命令格式符合 Murideo 协议规范

---

#### REQ-MUR-005 测量时自动设置

**优先级**: 中
**描述**: 系统应支持"测量时自动设置"选项。启用后，每次触发 CA-410 测量前自动将当前 Murideo 面板的参数（HDR/SDR、窗口大小、IRE 等）发送到 Murideo 设备。

**验收标准**:
1. 复选框控制该功能的启用/禁用
2. 启用时每次测量前自动发送 Murideo 参数
3. 自动设置在后台线程中执行，不阻塞 UI

---

#### REQ-MUR-006 BT.2020 设置

**优先级**: 中
**描述**: 系统应支持启用或禁用 BT.2020 宽色域标准。命令格式: `SENDSINGLE||112,{value}`，其中 0=禁用，1=启用。

**验收标准**:
1. 正确发送 BT.2020 命令
2. HDR 模式下默认启用 BT.2020，SDR 模式下默认禁用

---

### 3.3 自动化测试

#### REQ-AUTO-001 JSON 方案驱动测试

**优先级**: 高
**描述**: 系统应支持从 JSON 文件加载测试方案。每个方案包含名称、描述、默认参数和测试步骤列表。步骤中未指定的参数继承方案默认值。

**JSON 方案格式**:
```json
{
  "name": "方案名称",
  "description": "方案描述",
  "defaults": {
    "timing": 34,
    "color_space": 0,
    "color_depth": 1,
    "pattern": 26,
    "hdr": 1,
    "bt2020": 1,
    "ire": 255,
    "window_size": 100
  },
  "steps": [
    {"hdr": 1, "bt2020": 1, "ire": 255, "window_size": 10, "note": "HDR10 10%窗口"},
    {"hdr": 0, "ire": 128, "window_size": 100, "note": "SDR 50%IRE"}
  ]
}
```

**验收标准**:
1. 正确解析 JSON 方案文件
2. 步骤中缺失的参数从 defaults 中继承
3. 方案加载后更新 Murideo 面板默认值
4. 支持列出 profiles 目录下所有 JSON 方案文件

---

#### REQ-AUTO-002 Excel 用例驱动测试

**优先级**: 高
**描述**: 系统应支持从 Excel 文件的"测试用例"工作表加载测试用例。工作表采用 12 列格式。

**Excel 工作表格式**:
- 工作表名称: "测试用例"
- 第 1 行: 分类标题行
- 第 2 行: 列标题行
- 第 3 行起: 数据行

| 列号 | 列名 | 说明 |
|------|------|------|
| 1 | 编号 | 测试用例编号，如 "T001" |
| 2 | 图像模式 | 标准/影院/电脑/鲜艳 |
| 3 | 峰值亮度 | 关/弱/中/强 |
| 4 | 当前背光值 | 数值，默认 100 |
| 5 | Local Dimming | 关/弱/中/强 |
| 6 | 小窗口大小 | 百分比，如 "10%"、"50%" |
| 7 | HDR/SDR | HDR 或 SDR |
| 8 | 白块亮度(nit) | IRE 等级 (0-255) |
| 9 | Lv (cd/m²) | 测量结果（初始为空） |
| 10 | x | 测量结果（初始为空） |
| 11 | y | 测量结果（初始为空） |
| 12 | 备注 | 补充说明 |

**验收标准**:
1. 正确读取"测试用例"工作表的所有数据行
2. 百分比字段（小窗口大小）正确解析（如 "10%" 解析为 10.0）
3. 空行或编号为空的行自动跳过

---

#### REQ-AUTO-003 自动测试流程

**优先级**: 高
**描述**: 系统应支持按照测试用例列表自动执行测试。对每个测试用例，执行以下步骤：

1. **检测 TV 参数变化**: 若当前用例的图像模式、峰值亮度、背光值或 Local Dimming 与上一用例不同，暂停并提示用户调整 TV 设置
2. **设置 Murideo 参数**: 将当前用例的 HDR/SDR、IRE、窗口大小等参数发送到 Murideo
3. **等待稳定延迟**: 等待可配置的稳定时间（默认 3 秒），使显示画面稳定
4. **触发 CA-410 测量**: 调用测量回调函数执行测量
5. **等待测量结果**: 测量完成后由 UI 通知 worker 推进
6. **写入 Excel**: 将测量结果写入 Excel 文件
7. **等待步间延迟**: 等待可配置的步间时间（默认 2 秒）
8. **推进到下一用例**: 递增用例索引，继续下一轮循环

**验收标准**:
1. 按序自动执行所有测试用例
2. 稳定延迟和步间延迟可配置
3. 延迟期间可响应停止操作
4. 测量结果正确写入 Excel
5. 全部用例完成后通知用户

---

#### REQ-AUTO-004 TV 参数变化检测

**优先级**: 高
**描述**: 当连续两个测试用例的 TV 相关参数（image_mode, peak_brightness, backlight_value, local_dimming）发生任何变化时，系统应暂停自动测试流程，弹出确认对话框，提示用户调整电视机设置。

**确认对话框内容**:
- 当前步骤编号
- 需要调整的 TV 参数：图像模式、峰值亮度、背光值、Local Dimming

**用户操作**:
- 点击"确定": 继续自动测试
- 点击"取消": 停止自动测试

**验收标准**:
1. TV 参数变化时正确触发暂停
2. 对话框显示变化的参数
3. 确认后从暂停点继续
4. 取消后停止测试

---

#### REQ-AUTO-005 暂停/恢复/停止

**优先级**: 高
**描述**: 系统应在自动测试过程中的任意时刻支持暂停、恢复和停止操作。

**验收标准**:
1. 暂停后恢复从精确暂停点继续
2. 停止后清理状态，可重新开始
3. 暂停期间不执行测量
4. 延迟等待期间（稳定延迟、步间延迟）也可响应停止

---

#### REQ-AUTO-006 增量命令发送

**优先级**: 中
**描述**: 在自动测试中设置 Murideo 参数时，系统应仅发送与上一步相比发生变化的参数，减少通信开销。IRE 初始化、Window 图案选择和 IRE/窗口大小命令每次都必须发送。

**增量策略**:
- 跟踪上一次发送的 Murideo 参数集合（hdr_mode, bt2020, color_depth, timing, color_space, pattern_id）
- 仅当参数值发生变化时才将其加入发送命令列表
- IRE 和窗口大小每次都发送（因为 IRE 模式状态不跨连接保持）

**验收标准**:
1. 未变化的参数不在命令中出现
2. 日志中记录跳过的参数名
3. IRE/窗口大小始终发送

---

### 3.4 数据记录与导出

#### REQ-DATA-001 测量历史记录

**优先级**: 中
**描述**: 系统应在可滚动的表格中显示所有测量结果，最多保留 1000 行。表格列与 Excel 格式一致，共 12 列：编号、图像模式、峰值亮度、当前背光值、Local Dimming、小窗口大小、HDR/SDR、白块亮度(nit)、Lv (cd/m²)、x、y、备注。

**验收标准**:
1. 每次测量结果自动追加到表格末尾
2. 表格自动滚动到最新记录
3. 超过 1000 行时自动移除最早的记录
4. 支持清空历史记录

---

#### REQ-DATA-002 Excel 回写

**优先级**: 高
**描述**: 系统应将测量结果回写到 Excel 测试用例文件中。匹配规则：通过 7 个字段（图像模式、峰值亮度、当前背光值、Local Dimming、小窗口大小、HDR/SDR、白块亮度(nit)）与测试用例行进行匹配。

**匹配规则**:
- 逐行比较 7 个匹配字段
- 百分比字段规范化：去掉 "%" 后缀
- 数值字段规范化：100.0 和 100 视为相同
- 比较不区分大小写

**写入规则**:
- 匹配成功: 在对应行写入 Lv、x、y 值
  - Lv 格式: 0.00
  - x, y 格式: 0.0000
- 未匹配: 追加到"额外数据"工作表

**验收标准**:
1. 正确匹配测试用例行
2. Lv、x、y 值正确写入对应单元格
3. 未匹配数据写入"额外数据"工作表
4. 返回匹配数和未匹配数

---

#### REQ-DATA-003 CSV 导出

**优先级**: 低
**描述**: 系统应支持将所有历史记录导出为 CSV 文件。

**CSV 格式要求**:
- 中文列标题，与 Excel 格式一致
- 编码: UTF-8 with BOM (utf-8-sig)
- 默认文件名: `ca410_{YYYYMMDD_HHMMSS}.csv`

**验收标准**:
1. 导出的 CSV 文件在 Excel 中可正确打开（无乱码）
2. 列标题为中文
3. 所有历史记录均被导出

---

### 3.5 配置管理

#### REQ-CFG-001 用户偏好持久化

**优先级**: 中
**描述**: 系统应保存和恢复以下用户偏好设置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| last_port | string \| null | null | 上次使用的 CA-410 串口 |
| mode | string | "xyLv" | 测量模式（"xyLv" 或 "TduvLv"） |
| continuous_interval | float | 1.0 | 连续测量间隔（秒） |
| window_geometry | string | "900x650" | 窗口大小和位置 |
| murideo_host | string | "192.168.1.239" | Murideo IP 地址 |
| murideo_transport | string | "websocket" | Murideo 传输方式（"websocket" 或 "serial"） |
| murideo_serial_port | string | "" | Murideo 串口 |
| murideo_serial_baudrate | int | 115200 | Murideo 串口波特率 |

**存储位置**:
- Windows: `%APPDATA%/ca410_reader/config.json`
- 其他系统: `~/.ca410_reader/config.json`

**配置文件格式**:
```json
{
  "last_port": "COM3",
  "mode": "xyLv",
  "continuous_interval": 1.0,
  "window_geometry": "950x700+100+100",
  "murideo_host": "192.168.1.239",
  "murideo_transport": "websocket",
  "murideo_serial_port": "",
  "murideo_serial_baudrate": 115200
}
```

**验收标准**:
1. 程序退出时保存当前配置
2. 程序启动时加载上次配置
3. 配置文件不存在时使用默认值
4. 仅保存已定义的配置项，忽略未知字段
5. 配置文件读写失败时静默处理，不影响程序运行

---

## 4 非功能需求

### 4.1 性能

| 编号 | 需求 | 说明 |
|------|------|------|
| NFR-PERF-001 | UI 响应性 | 所有硬件 I/O 操作在后台线程中执行，UI 线程（tkinter 主循环）不得被阻塞 |
| NFR-PERF-002 | 队列轮询频率 | UI 通过 `tkinter.after()` 以 100ms 间隔轮询结果队列 |
| NFR-PERF-003 | 连续测量间隔 | 连续测量最小间隔可配置，默认 1.0 秒 |

### 4.2 可靠性

| 编号 | 需求 | 说明 |
|------|------|------|
| NFR-REL-001 | ER10 自动重试 | CA-410 测量返回 ER10 时自动执行零点校准后重试测量一次 |
| NFR-REL-002 | WebSocket 自动重连 | WebSocket 连接断开后自动重连，最多 3 次，采用指数退避策略（1s, 2s, 4s） |
| NFR-REL-003 | 串口握手验证 | Murideo 串口连接后发送握手命令验证设备响应 |
| NFR-REL-004 | 误设备检测 | Murideo 串口连接时检测是否误连接了 CA-410（通过 ERxx 错误码识别） |
| NFR-REL-005 | 连接断开保护 | 连续测量中若 CA-410 连接断开，自动停止测量并通知用户 |

### 4.3 易用性

| 编号 | 需求 | 说明 |
|------|------|------|
| NFR-USA-001 | 中文界面 | 所有界面文字、错误消息、对话框均使用中文 |
| NFR-USA-002 | CJK 字体支持 | 自动检测系统可用的 CJK 字体（Microsoft YaHei、SimHei、SimSun、WenQuanYi 等），确保中文正常显示 |
| NFR-USA-003 | 串口自动发现 | CA-410 串口支持自动发现，无需用户手动输入 COM 端口号 |
| NFR-USA-004 | 中文错误提示 | 所有设备通信错误均以中文提示用户，包含故障排查建议 |

### 4.4 可维护性

| 编号 | 需求 | 说明 |
|------|------|------|
| NFR-MAIN-001 | 模块化架构 | 采用 UI / Worker / Driver / Transport 四层架构，各层职责清晰，便于独立修改和测试 |
| NFR-MAIN-002 | JSON 方案扩展 | 新增测试场景无需修改代码，只需创建 JSON 方案文件 |
| NFR-MAIN-003 | 文件日志 | 所有设备通信和关键操作均记录到日志文件，便于问题排查 |

### 4.5 可部署性

| 编号 | 需求 | 说明 |
|------|------|------|
| NFR-DEP-001 | 单文件 EXE | 通过 PyInstaller 打包为 Windows 单文件可执行程序（CA410Reader.exe） |
| NFR-DEP-002 | 无需 Python 环境 | 最终用户无需安装 Python 运行时或任何依赖包 |
| NFR-DEP-003 | 资源文件打包 | profiles 目录和模板 Excel 文件随 EXE 一起打包 |

---

## 5 数据结构定义

### 5.1 XyLvResult — xyLv 测量结果

| 字段 | 类型 | 说明 |
|------|------|------|
| lv | float | 亮度值 (cd/m²) |
| x | float | 色度坐标 x |
| y | float | 色度坐标 y |
| timestamp | datetime | 测量时间（自动生成） |
| image_mode | str | 图像模式 |
| window_ratio | float \| None | 窗口大小百分比 |
| window_brightness | float \| None | IRE 亮度等级 |
| peak_brightness | str | 峰值亮度模式 |
| backlight_value | float \| None | 背光值 |
| local_dimming | str | Local Dimming 模式 |
| hdr_sdr | str | HDR/SDR 模式 |
| note | str | 备注 |

### 5.2 TduvLvResult — TduvLv 测量结果

| 字段 | 类型 | 说明 |
|------|------|------|
| lv | float | 亮度值 (cd/m²) |
| tcp | float | 色温 (K) |
| duv | float | duv 偏差值 |
| timestamp | datetime | 测量时间（自动生成） |
| image_mode | str | 图像模式 |
| window_ratio | float \| None | 窗口大小百分比 |
| window_brightness | float \| None | IRE 亮度等级 |
| peak_brightness | str | 峰值亮度模式 |
| backlight_value | float \| None | 背光值 |
| local_dimming | str | Local Dimming 模式 |
| hdr_sdr | str | HDR/SDR 模式 |
| note | str | 备注 |

### 5.3 TestCase — 测试用例

| 字段 | 类型 | 说明 |
|------|------|------|
| row | int | Excel 行号（1-indexed） |
| test_id | str | 编号，如 "T001" |
| image_mode | str | 图像模式 |
| peak_brightness | str | 峰值亮度 |
| backlight_value | float | 当前背光值 |
| local_dimming | str | Local Dimming |
| window_size | float | 小窗口大小 (%) |
| hdr_sdr | str | HDR/SDR |
| window_brightness | float | IRE 等级 (0-255) |
| note | str | 备注 |
| timing | int \| None | 信号格式 ID（可选） |
| color_space | int \| None | 色彩空间 ID（可选） |
| color_depth | int \| None | 色深 ID（可选） |
| pattern | int \| None | 图案 ID（可选） |

### 5.4 TestProfile — 测试方案

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 方案名称 |
| description | str | 方案描述 |
| defaults | dict | 默认参数集合 |
| steps | list[TestStep] | 测试步骤列表 |
| filepath | str | 方案文件路径 |

### 5.5 TestStep — 测试步骤

| 字段 | 类型 | 说明 |
|------|------|------|
| hdr | int \| None | HDR 模式 (0=SDR, 1=HDR10, 2=HLG) |
| bt2020 | int \| None | BT.2020 (0=禁用, 1=启用) |
| ire | int \| None | IRE 亮度 (0-255) |
| window_size | int \| None | 窗口大小 (0-100%) |
| timing | int \| None | 信号格式 ID |
| color_space | int \| None | 色彩空间 ID |
| color_depth | int \| None | 色深 ID |
| pattern | int \| None | 图案 ID |
| note | str | 备注 |

所有字段均为可选，缺失值从 TestProfile.defaults 中继承。

### 5.6 Excel 工作表格式

**工作表名称**: "测试用例"

| 列号 | 列名 | 数据类型 | 说明 |
|------|------|---------|------|
| 1 | 编号 | string | 测试用例编号 |
| 2 | 图像模式 | string | 标准等 |
| 3 | 峰值亮度 | string | 关/弱/中/强 |
| 4 | 当前背光值 | numeric | 背光数值 |
| 5 | Local Dimming | string | 关/弱/中/强 |
| 6 | 小窗口大小 | string | 如 "10%" |
| 7 | HDR/SDR | string | HDR 或 SDR |
| 8 | 白块亮度(nit) | numeric | IRE 等级 |
| 9 | Lv (cd/m²) | float | 亮度测量结果，格式 0.00 |
| 10 | x | float | 色度 x 测量结果，格式 0.0000 |
| 11 | y | float | 色度 y 测量结果，格式 0.0000 |
| 12 | 备注 | string | 补充说明 |

### 5.7 JSON 方案格式

```json
{
  "name": "string — 方案名称",
  "description": "string — 方案描述",
  "defaults": {
    "timing": "int — 信号格式 ID",
    "color_space": "int — 色彩空间 ID",
    "color_depth": "int — 色深 ID",
    "pattern": "int — 图案 ID",
    "hdr": "int — HDR 模式",
    "bt2020": "int — BT.2020 开关",
    "ire": "int — IRE 亮度",
    "window_size": "int — 窗口大小百分比"
  },
  "steps": [
    {
      "hdr": "int | 省略 — 步骤覆盖",
      "bt2020": "int | 省略 — 步骤覆盖",
      "ire": "int | 省略 — 步骤覆盖",
      "window_size": "int | 省略 — 步骤覆盖",
      "timing": "int | 省略 — 步骤覆盖",
      "color_space": "int | 省略 — 步骤覆盖",
      "color_depth": "int | 省略 — 步骤覆盖",
      "pattern": "int | 省略 — 步骤覆盖",
      "note": "string | 省略 — 步骤备注"
    }
  ]
}
```

### 5.8 配置文件格式

```json
{
  "last_port": "string | null — 上次 CA-410 串口",
  "mode": "xyLv | TduvLv — 测量模式",
  "continuous_interval": "float — 连续测量间隔（秒）",
  "window_geometry": "string — 窗口几何信息",
  "murideo_host": "string — Murideo IP 地址",
  "murideo_transport": "websocket | serial — Murideo 传输方式",
  "murideo_serial_port": "string — Murideo 串口",
  "murideo_serial_baudrate": "int — Murideo 串口波特率"
}
```

---

## 6 约束与假设

### 6.1 硬件约束

| 编号 | 约束 | 说明 |
|------|------|------|
| CON-HW-001 | CA-410 通信参数 | CA-410 必须使用 CA-S40 协议，固定 38400 波特率、8N1 格式，不可更改 |
| CON-HW-002 | Murideo 串口波特率 | Murideo 串口波特率由用户配置（默认 115200），实际值厂商未正式文档化 |
| CON-HW-003 | IRE 模式状态 | IRE 模式状态不跨连接保持，每次连接后必须重新初始化（发送 SENDOTHER\|63739） |
| CON-HW-004 | CA-410 单探头限制 | 单探头 CA-410 不支持 PSC（探头选择）命令，连接时须跳过该步骤 |

### 6.2 协议约束

| 编号 | 约束 | 说明 |
|------|------|------|
| CON-PROTO-001 | 色度值格式 | CA-410 返回的色度值 x, y 省略 "0." 前缀（如 "230" 表示 0.230），解析时需补全 |
| CON-PROTO-002 | 响应类别偏移 | Murideo 响应中的类别值 = 命令类别值 + 32768（如 PATTERN 98 对应响应 32866） |
| CON-PROTO-003 | IRE/窗口命令时序 | IRE/窗口设置命令要求在图案选择（SENDDOUBLE\|98,26）和 IRE 值命令（SENDOTHER\|30971）之间等待 700ms |
| CON-PROTO-004 | PSC 命令兼容性 | CA-410 单探头型号不支持 PSC 命令，发送后返回 ER10，须捕获 UndefinedCommandError 异常并跳过 |

### 6.3 操作假设

| 编号 | 假设 | 说明 |
|------|------|------|
| ASM-OPS-001 | 物理接触 TV | 用户可以物理接触电视机以调整图像设置（图像模式、背光等软件无法控制的参数） |
| ASM-OPS-002 | 探头盖可用 | 用户拥有 CA-410 探头盖，可在零点校准时使用 |
| ASM-OPS-003 | 设备已就绪 | CA-410 和 Murideo 在使用前已开机并正确连接 |
| ASM-OPS-004 | 网络连通性 | 使用 WebSocket 连接 Murideo 时，PC 和 Murideo 处于同一局域网 |

---

## 7 参考文档

| 编号 | 文档名称 | 说明 |
|------|---------|------|
| REF-001 | CA-S40 Communication Protocol (ca-sdk2_en-US.pdf) | CA-410 串口通信协议规范 |
| REF-002 | Murideo Seven G8K Manual (MU-GEN-SEVEN-G8K-Manual.pdf) | Murideo Seven G8K 用户手册 |
| REF-003 | Murideo Seven G8K Protocol Reference (murideo-seven-g8k-protocol.md) | Murideo Seven G8K 协议参考文档 |
