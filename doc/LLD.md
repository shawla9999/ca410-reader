# PqReadTool 详细设计文档

## 1. 引言

本文档基于概要设计（HLD），对各模块的内部设计进行详细说明，包括类接口、关键算法、状态转换和协议细节。

---

## 2. CA-410 驱动模块详细设计

### 2.1 CA410Driver 类接口

| 方法 | 参数 | 返回值 | 异常 | 说明 |
|------|------|--------|------|------|
| `__init__` | `port: str \| None = None` | - | - | 初始化驱动 |
| `discover_port` | - | `str \| None` | - | 扫描串口自动发现 CA-410 |
| `connect` | `port: str \| None = None` | `None` | `ConnectionError` | 打开串口并进入远程模式 |
| `disconnect` | - | `None` | - | 退出远程模式并关闭串口 |
| `is_connected` | (property) | `bool` | - | 串口打开且处于远程模式 |
| `set_mode` | `mode: MeasurementMode` | `None` | `CA410Error` | 设置测量显示模式 |
| `measure` | - | `XyLvResult \| TduvLvResult` | `CA410Error` | 执行测量并解析结果 |
| `zero_calibrate` | - | `None` | `CA410Error` | 零点校准 |

类常量：`BAUDRATE=38400`，`BYTESIZE=EIGHTBITS`，`PARITY=PARITY_NONE`，`STOPBITS=STOPBITS_ONE`，`TIMEOUT=2.0`

### 2.2 连接序列

1. 打开串口（38400/8N1，无硬件流控）
2. 发送 `COM,1` 进入远程模式 → 等待 **500ms**
3. 发送 `PSC,1` 选择探头 1 → 捕获 `UndefinedCommandError`（单探头机型不支持）→ 等待 **100ms**
4. 发送 `MDS,0` 设置 xyLv 显示模式 → 等待 **200ms**
5. 发送 `ZRC` 零点校准 → 捕获 `CA410Error`（探头盖未盖）
6. 设置 `_in_remote_mode = True`

### 2.3 测量与自动重试

```
发送 MES 命令
├── 返回正常数据 → 解析并返回结果
└── 返回 ER10（未定义命令）
    ├── 发送 ZRC 零点校准
    ├── 重试 MES
    │   ├── 成功 → 返回结果
    │   └── 仍失败 → 抛出 CA410Error
    └── 校准失败 → 抛出 CA410Error
```

### 2.4 响应解析规则

**xyLv 模式**：`OK00,P1 {x};{y};{Lv}`

- x/y 色度值**省略 "0." 前缀**（如 `"230"` = 0.230）
- Lv 含小数点
- 探头前缀 `"P1 "` 需去除

**TduvLv 模式**：`OK00,P1 {Lv};{Tcp};{duv}`

- 三个值均含小数点
- 解析顺序为 Lv;Tcp;duv（与 xyLv 不同）

**色度值解析** (`_parse_chromaticity`)：若字符串不含小数点则添加 `"0."` 前缀。

### 2.5 错误码映射

| 错误码 | 异常类 | 中文说明 |
|--------|--------|----------|
| ER00 | `CommandError` | 命令错误或通信错误 |
| ER02 | `CA410Error` | 因条件不满足而强制终止测量 |
| ER05 | `OutOfRangeError` | 测量值超出可显示范围 (0.01 - 100,000 cd/m²) |
| ER10 | `UndefinedCommandError` | 未定义命令 |
| ER11 | `UnacceptableCommandError` | 当前状态下不可接受的命令 |
| ER13 | `InvalidDataError` | 无效数据或参数 |
| ER17 | `InsufficientProbesError` | 探头数量不足 |
| ER19 | `NoCalibrationDataError` | 无有效校准数据 |
| ER20 | `CA410Error` | 内存数据访问错误 |
| ER21 | `ZeroCalibrationError` | 零点校准错误 |
| ER30 | `ZeroCalibrationError` | 零点校准错误 |
| ER31 | `CA410Error` | 内存读写错误 |
| ER52 | `CA410Error` | EEPROM 访问错误 |
| ER80 | `ConnectionError` | USB 通信错误 |
| ER99 | `CA410Error` | 探头程序错误 |

### 2.6 数据类型定义

**MeasurementMode(IntEnum)**

| 值 | 名称 | 说明 |
|----|------|------|
| 0 | `XY_LV` | 色度+亮度模式 (x, y, Lv) |
| 2 | `TDUV_LV` | 色温+亮度模式 (Tcp, duv, Lv) |

**ConnectionStatus(IntEnum)**

| 值 | 名称 | 说明 |
|----|------|------|
| 0 | `DISCONNECTED` | 未连接 |
| 1 | `CONNECTING` | 连接中 |
| 2 | `CONNECTED` | 已连接 |
| 3 | `ERROR` | 连接错误 |

**XyLvResult**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `lv` | `float` | 必填 | 亮度 (cd/m²) |
| `x` | `float` | 必填 | 色度 x |
| `y` | `float` | 必填 | 色度 y |
| `timestamp` | `datetime` | `datetime.now()` | 测量时间 |
| `image_mode` | `str` | `''` | 图像模式 |
| `window_ratio` | `float \| None` | `None` | 窗口大小 (%) |
| `window_brightness` | `float \| None` | `None` | 白块亮度 (IRE) |
| `peak_brightness` | `str` | `''` | 峰值亮度 |
| `backlight_value` | `float \| None` | `None` | 背光值 |
| `local_dimming` | `str` | `''` | Local Dimming |
| `hdr_sdr` | `str` | `''` | HDR/SDR |
| `note` | `str` | `''` | 备注 |

**TduvLvResult**：`lv: float`, `tcp: float`, `duv: float`，其余元数据字段与 XyLvResult 相同。

---

## 3. Murideo 驱动模块详细设计

### 3.1 MurideoDriver 类接口

| 方法 | 参数 | 返回值 | 异常 | 说明 |
|------|------|--------|------|------|
| `__init__` | `transport_type: str = 'websocket'` | - | - | 初始化驱动 |
| `configure` | `host: str` | `None` | - | 配置 WebSocket 连接目标 |
| `configure_serial` | `port, baudrate=115200, bytesize, parity, stopbits` | `None` | - | 配置串口连接参数 |
| `connect` | `host: str \| None = None` | `None` | `MurideoConnectionError` | 连接设备（含握手验证） |
| `disconnect` | - | `None` | - | 断开连接 |
| `set_ire_window` | `ire, window_size, hdr_mode?, bt2020?, color_depth?, timing?, color_space?, pattern_id?` | `None` | `MurideoError` | 设置 IRE 亮度和窗口大小 |
| `set_hdr` | `mode: int` | `None` | `MurideoError` | 设置 HDR 模式 |
| `set_sdr` | - | `None` | `MurideoError` | 设置 SDR (HDR=0) |
| `set_hdr10` | - | `None` | `MurideoError` | 设置 HDR10 (HDR=1) |
| `set_hlg` | - | `None` | `MurideoError` | 设置 HLG (HDR=2) |
| `set_timing` | `timing_id: int` | `None` | `MurideoError` | 设置视频时序 |
| `set_pattern` | `pattern_id: int` | `None` | `MurideoError` | 设置测试图案 |
| `set_color_space` | `value: int` | `None` | `MurideoError` | 设置色彩空间 |
| `set_color_depth` | `value: int` | `None` | `MurideoError` | 设置色深 |
| `write_all` | `hdr_mode?, pattern_id?` | `dict` | - | 批量设置 HDR 和图案 |
| `send_command` | `command: str` | `str \| None` | `MurideoError` | 发送原始命令 |
| `send_sendsingle` | `category: int, value` | `str \| None` | `MurideoError` | 构建并发送 SENDSINGLE |
| `send_senddouble` | `category: int, value` | `str \| None` | `MurideoError` | 构建并发送 SENDDOUBLE |
| `send_sendother` | `category: int, *values` | `str \| None` | `MurideoError` | 构建并发送 SENDOTHER |

Properties: `is_connected→bool`, `host→str`, `transport_type→str`, `serial_port→str`

类常量：`DEFAULT_IP='192.168.1.239'`，`WS_PATH='/ws/uart'`，`RECV_TIMEOUT=2.0`

### 3.2 异常类

| 异常类 | 继承 | 说明 |
|--------|------|------|
| `MurideoError` | `Exception` | 基础异常 |
| `MurideoConnectionError` | `MurideoError` | 连接失败 |
| `MurideoTimeoutError` | `MurideoError` | 设备无响应 |
| `MurideoCommandError` | `MurideoError` | 命令被拒绝或错误响应 |

### 3.3 连接流程

**WebSocket 路径**：

1. 创建 `WebSocketTransport`
2. 调用 `transport.connect(url=ws_url, timeout=2.0)`
3. 验证连接状态

**Serial 路径**：

1. 创建 `SerialTransport`
2. 调用 `transport.connect(port, baudrate, ...)`
3. 发送握手命令 `SENDSINGLE||111,0`
4. 检查响应：
   - 含 `RESPONSE` → 握手成功
   - 以 `ER` 开头 → 检测到 CA-410，报错"连接了错误的设备"
   - 无响应 → 报错"设备无响应，请检查波特率"
5. 握手失败时自动断开连接

### 3.4 IRE/窗口控制命令序列

| 步骤 | 命令 | 可选 | 说明 |
|------|------|------|------|
| 1 | `SENDSINGLE\|\|97,{timing}` | 是 | 设置信号格式 |
| 2 | `SENDSINGLE\|\|99,{color_space}` | 是 | 设置色彩空间 |
| 3 | `SENDSINGLE\|\|111,{hdr_mode}` | 是 | 设置 HDR 模式 |
| 4 | `SENDSINGLE\|\|112,{bt2020}` | 是 | 设置 BT.2020 |
| 5 | `SENDSINGLE\|\|100,{color_depth}` | 是 | 设置色深 |
| 6 | `SENDOTHER\|\|63739` | 否 | 初始化 IRE 模式（每次必须发送） |
| 7 | `SENDDOUBLE\|\|98,{pattern_id}` | 否 | 选择 Window 图案（默认 26） |
| 8 | 等待 **700ms** | 否 | Window 图案生效的必要延迟 |
| 9 | `SENDOTHER\|\|30971,{IRE},{window_size}` | 否 | 设置 IRE 亮度 + 窗口大小 |

**关键约束**：
- 步骤 6-9 每次调用都必须发送，IRE 模式状态不会跨连接保持
- 700ms 延迟是 Window 图案命令到 IRE 值命令的必要间隔
- 所有命令通过 `send_batch` 在单次连接中发送
- `send_batch` 返回响应列表，全部无响应时抛出 `MurideoTimeoutError`，含 ER 响应时抛出 `MurideoCommandError`

### 3.5 命令构建与响应解析

**命令格式**：`\r\n{FUNCTION}||{CATEGORY},{VALUE}\r\n`

| 函数 | 用途 | 典型 Category |
|------|------|---------------|
| `SENDSINGLE` | 大部分设置 | 时序、色彩空间、色深、HDR、BT.2020 |
| `SENDDOUBLE` | 图案和音频 | 测试图案、Dolby/DTS |
| `SENDOTHER` | 特殊命令 | IRE 初始化、IRE 窗口、恢复出厂 |

**响应格式**：`RESPONSE||{32768+CATEGORY}||{VALUE}\r\n`

- 偏移量：响应 category = 命令 category + 32768
- 例：发送 `SENDSINGLE||111,1`（HDR=HDR10）→ 响应 `RESPONSE||32879||1`

**Category 常量**：

| 常量 | ID | 函数 | 说明 |
|------|-----|------|------|
| `CAT_TIMING` | 97 | SENDSINGLE | 视频时序 |
| `CAT_PATTERN` | 98 | SENDDOUBLE | 测试图案 |
| `CAT_COLOR_SPACE` | 99 | SENDSINGLE | 色彩空间 |
| `CAT_COLOR_DEPTH` | 100 | SENDSINGLE | 色深 |
| `CAT_HDR` | 111 | SENDSINGLE | HDR 模式 |
| `CAT_BT2020` | 112 | SENDSINGLE | BT.2020 |
| `CAT_FACTORY_RESET` | 30722 | SENDOTHER | 恢复出厂 |
| `CAT_FAN` | 30723 | SENDSINGLE | 风扇控制 |
| `CAT_IRE_WINDOW` | 30971 | SENDOTHER | IRE 亮度+窗口大小 |
| `CAT_IRE_INIT` | 63739 | SENDOTHER | IRE 模式初始化 |

**HDR 值**：`HDR_OFF=0`, `HDR_HDR10=1`, `HDR_HLG=2`

**图案 ID**：`PATTERN_WINDOW=26`, `PATTERN_WHITE_SCREEN=11`, `PATTERN_BLACK_SCREEN=10`, `PATTERN_100_COLOR_BARS=0`, `PATTERN_DVS_WHITE_LEVEL_1/2/3=50/51/52`

### 3.6 错误处理

| 条件 | 抛出异常 | 说明 |
|------|----------|------|
| `send_and_recv` 返回 `None` | `MurideoTimeoutError` | 设备无响应 |
| 响应以 `ER` 开头 | `MurideoCommandError` | 可能连接了 CA-410 等错误设备 |
| `ConnectionError` | `MurideoConnectionError` | 连接已断开 |
| `send_batch` 全部无响应 | `MurideoTimeoutError` | 所有命令均未收到回复 |
| `send_batch` 含 ER 响应 | `MurideoCommandError` | 收到错误响应 |

---

## 4. 传输层详细设计

### 4.1 抽象接口 MurideoTransport

```
class MurideoTransport(ABC):
    connect(**kwargs) -> None
    disconnect() -> None
    is_connected() -> bool
    send_and_recv(command: str, timeout: float = 5.0) -> str | None
    send_batch(commands: list[str], delays: list[float] | None, timeout: float = 5.0) -> list[str | None]
```

### 4.2 WebSocketTransport

**内部架构**：

- 专用 `asyncio` 事件循环运行在 daemon 线程上
- 线程安全调用通过 `asyncio.run_coroutine_threadsafe` + `future.result(timeout)` 阻塞等待
- `connected_event`（`threading.Event`）用于启动同步
- `stop_event`（`threading.Event`）用于关闭

**常量**：`HEARTBEAT_INTERVAL=30.0s`, `HEARTBEAT_TIMEOUT=60.0s`, `MAX_RECONNECT=3`

**心跳机制**：

- 每 30 秒发送 WebSocket ping
- 超时 60 秒
- 失败触发重连流程

**重连策略**：

- 指数退避：`2^reconnect_count` 秒（第 1 次 1s，第 2 次 2s，第 3 次 4s）
- 最多 3 次重连
- 超过次数后放弃

**批量命令**：

- `send_batch` 支持每条命令间插入延迟（用于 IRE/Window 序列的 700ms 延迟）
- 每条命令独立 `send` + `recv`
- 超时一条不影响后续

### 4.3 SerialTransport

**串口配置**：

- 默认 `115200/8N1`
- 所有参数（波特率、数据位、校验、停止位）用户可配置
- `timeout` 和 `write_timeout` 使用相同值

**握手验证** (`_handshake`)：

1. 发送 `SENDSINGLE||111,0`
2. 期望响应含 `RESPONSE`
3. 返回 `True`/`False`

**回声过滤与分帧** (`_read_response`)：

设备会回显发送的命令，需要过滤：

| 行内容 | 判断 | 处理 |
|--------|------|------|
| 以 `RESPONSE` 开头 | 有效响应 | 保留（更新 `last_response`） |
| 含 `\|\|` 但不以 `RESPONSE` 开头 | 命令回显 | 跳过 |
| 其他 | 数据行 | 保留（作为 `last_response` 备选） |

**分帧逻辑**：

1. deadline 循环（基于 `time.monotonic()`）
2. 50ms 轮询 `ser.in_waiting`
3. 收到数据后若 50ms 内无新数据，认为传输结束
4. 按换行符分割处理完整行
5. 返回最后一个 `RESPONSE` 行，或最后一行，或 `None`

---

## 5. Worker 模块详细设计

### 5.1 MeasurementWorker

**消息类型常量**：

| 常量 | 值 | 说明 |
|------|-----|------|
| `RESULT_SINGLE` | `'single'` | 单次测量结果 |
| `RESULT_CONTINUOUS` | `'continuous'` | 连续测量结果 |
| `RESULT_ERROR` | `'error'` | 测量错误 |
| `STATUS_CONNECTED` | `'connected'` | CA-410 已连接 |
| `STATUS_DISCONNECTED` | `'disconnected'` | CA-410 已断开 |
| `STATUS_CALIBRATING` | `'calibrating'` | 正在零点校准 |
| `STATUS_CALIBRATED` | `'calibrated'` | 零点校准完成 |

**接口**：

| 方法 | 参数 | 线程模型 | 说明 |
|------|------|----------|------|
| `__init__` | `result_queue: queue.Queue` | - | 创建内部 CA410Driver |
| `connect` | `port: str \| None` | daemon 线程 | `discover_port` → `driver.connect` → push `STATUS_CONNECTED` 或 `RESULT_ERROR` |
| `disconnect` | - | 同步 | 停止连续测量 → `driver.disconnect` → push `STATUS_DISCONNECTED` |
| `measure_single` | `mode: MeasurementMode \| None` | daemon 线程 | `set_mode` → `driver.measure` → push `RESULT_SINGLE` |
| `start_continuous` | `interval=1.0, mode=None` | 持久 daemon 线程 | 循环 `measure` → `queue` → `stop_event.wait(interval)` |
| `stop_continuous` | - | 同步 | 设置 `stop_event` → join 线程（3s 超时） |
| `zero_calibrate` | - | daemon 线程 | push `STATUS_CALIBRATING` → `driver.zero_calibrate` → push `STATUS_CALIBRATED` |
| `set_mode` | `mode: MeasurementMode` | daemon 线程 | `driver.set_mode` |

**连续测量循环**：

```python
while not stop_event.is_set():
    result = driver.measure()
    queue.put((RESULT_CONTINUOUS, result))
    stop_event.wait(interval)  # 可被 stop() 提前唤醒

# ConnectionError 时：设置 stop_event, push STATUS_DISCONNECTED
```

### 5.2 AutoTestWorker

**消息类型常量**：

| 常量 | 说明 |
|------|------|
| `AUTO_TEST_STARTED` | 自动测试已启动 |
| `AUTO_TEST_PROGRESS` | 测试进度更新（含 index, total, case） |
| `AUTO_TEST_ALL_DONE` | 所有测试完成 |
| `AUTO_TEST_ERROR` | 测试错误 |
| `AUTO_TEST_STOPPED` | 测试已停止 |
| `AUTO_TEST_TV_CONFIRM` | TV 参数变更，等待用户确认 |

**接口**：

| 方法 | 参数 | 说明 |
|------|------|------|
| `__init__` | `result_queue, murideo: MurideoDriver` | 初始化 |
| `configure` | `cases, excel_path, start_index=0, profile=None` | 配置测试用例 |
| `set_measure_callback` | `callback` | 设置 CA-410 测量回调 |
| `set_settle_delay` | `seconds: float (min 0)` | Murideo 设置后等待时间（默认 3s） |
| `set_step_delay` | `seconds: float (min 0)` | 测量完成后等待时间（默认 2s） |
| `confirm_tv_params` | - | 用户确认 TV 参数已调整 |
| `start` | - | 启动 daemon 线程运行 `_run` |
| `pause` | - | 设置 `_paused` 和 `_pause_event` |
| `resume` | - | 清除 `_paused` 和 `_pause_event` |
| `stop` | - | 设置 `_stop_event`，清除 `_pause_event` |
| `advance` | - | 通知当前测量完成（设置 `_pause_event`） |

Properties: `is_running→bool`, `is_paused→bool`, `current_index→int`, `total_cases→int`, `current_case→TestCase|None`

**TV 参数变更检测**：

- `_TV_PARAMS = ('image_mode', 'peak_brightness', 'backlight_value', 'local_dimming')`
- `_tv_params_changed(prev, curr)` 比较连续测试用例的这 4 个字段
- 任一不同 → 推送 `AUTO_TEST_TV_CONFIRM` → 等待 `_tv_confirm_event` → 用户调用 `confirm_tv_params()`

**增量命令发送** (`_set_murideo`)：

- `_prev_murideo_params` 字典追踪上次发送的参数
- 每步仅发送与上次不同的参数到 `murideo.set_ire_window()`
- IRE 初始化 + Window 图案 + IRE/大小**始终发送**（不受增量优化影响）
- 日志记录跳过的参数

**_run() 主循环**：

```
对每个测试用例:
  1. 检查 TV 参数变化 → 等待 _tv_confirm_event
  2. _set_murideo(case) 增量设置
  3. 推送 AUTO_TEST_PROGRESS
  4. 等待 settle_delay（0.5s 分片，可停止）
  5. _measure_callback() 触发测量
  6. 等待 advance() 通过 _pause_event
  7. 等待 step_delay（0.5s 分片，可停止）
```

**中断处理**：

- 所有 sleep 循环分解为 0.5s 分片检查 `stop_event`
- `pause_event.wait()` 可被 `advance()` 中断
- `stop()` 清除 `pause_event` 解除阻塞等待

---

## 6. UI 模块详细设计

### 6.1 MainWindow

**面板布局**（Grid 4 行）：

| 行 | 列 0 | 列 1 |
|----|------|------|
| 0 | ConnectionPanel（2 列跨） | |
| 1 | MeasurementPanel（2 列跨） | |
| 2 | MurideoPanel | ControlPanel |
| 3 | HistoryPanel（2 列跨） | |

最小尺寸：950×650

**事件路由表**：

| 消息类型 | 处理动作 |
|----------|----------|
| `RESULT_SINGLE` | 附加用户输入 → 更新测量面板 → 添加历史 → Excel 写入 |
| `RESULT_CONTINUOUS` | 同 RESULT_SINGLE |
| `RESULT_ERROR` | 显示错误 |
| `STATUS_CONNECTED` | 更新连接状态为已连接 |
| `STATUS_DISCONNECTED` | 更新连接状态为未连接 |
| `STATUS_CALIBRATING` | 显示"正在零点校准..." |
| `STATUS_CALIBRATED` | 显示"零点校准完成" |
| `MURIDEO_CONNECTED` | 更新面板状态 + 显示连接信息（含波特率） |
| `MURIDEO_DISCONNECTED` | 更新面板状态为未连接 |
| `MURIDEO_SET_RESULT` | 显示设置结果 |
| `MURIDEO_ERROR` | 显示错误 |
| `AUTO_TEST_STARTED` | 标记自动测试运行中 |
| `AUTO_TEST_PROGRESS` | 更新面板字段 + 进度显示 |
| `AUTO_TEST_ALL_DONE` | 标记自动测试完成 |
| `AUTO_TEST_STOPPED` | 标记自动测试已停止 |
| `AUTO_TEST_TV_CONFIRM` | 显示 TV 参数确认对话框 |
| `AUTO_TEST_ERROR` | 显示错误 |

**回调连接**：`murideo_connect`, `murideo_disconnect`, `murideo_set`, `autotest_start/pause/stop`, `profile_load`

**测量结果附加** (`_attach_user_inputs`)：从面板读取当前状态（image_mode, window_ratio 等）附加到测量结果对象

**Excel 自动写入** (`_auto_write_excel`)：检查 Excel 写入启用 → 转换结果为 record 字典 → 调用 `export_to_excel()`

### 6.2 ConnectionPanel

- COM 端口下拉框 + 刷新按钮
- 连接/断开按钮
- 状态画布指示器：灰色（未连接）、黄色（连接中）、绿色（已连接）、红色（错误）

### 6.3 MeasurementPanel

- 紧凑单行显示
- Lv：等宽 18pt 粗体
- x/y 或 Tcp/duv：模式切换时动态显示/隐藏

### 6.4 ControlPanel

6 个功能区：

1. **测量按钮**：单次 / 连续 / 零点校准
2. **模式+间隔**：xyLv/TduvLv 选择 + 连续测量间隔
3. **TV 参数**：图像模式、峰值亮度、背光值、Local Dimming、备注
4. **测试方案**：JSON 方案选择
5. **Excel 写入**：文件选择 + 自动写入复选框
6. **自动测试**：开始/暂停/停止 + 稳定延迟 + 步进延迟 + 进度显示

### 6.5 MurideoPanel

- 连接方式选择（WebSocket / Serial）
- IP 或串口 + 波特率
- 连接/断开按钮
- "设置到 Murideo" 按钮 + 自动设置复选框
- 参数控制：HDR/SDR、窗口大小 (%)、IRE Level (0-255)、信号格式、色彩空间、测试图案、色深
- 串口列表标记：CA-410 设备标记为 `[CA-410]` 避免选错端口

### 6.6 HistoryPanel

- `Treeview` 表格，12 列，最大 1000 行
- 清除按钮
- `_all_data` 列表用于 CSV 导出

---

## 7. Util 模块详细设计

### 7.1 AppConfig

**DEFAULTS**：

| 键 | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `last_port` | `str \| None` | `None` | 上次使用的串口 |
| `mode` | `str` | `'xyLv'` | 测量模式 |
| `continuous_interval` | `float` | `1.0` | 连续测量间隔（秒） |
| `window_geometry` | `str` | `'900x650'` | 窗口尺寸 |
| `murideo_host` | `str` | `'192.168.1.239'` | Murideo IP 地址 |
| `murideo_transport` | `str` | `'websocket'` | Murideo 连接方式 |
| `murideo_serial_port` | `str` | `''` | Murideo 串口号 |
| `murideo_serial_baudrate` | `int` | `115200` | Murideo 波特率 |

**加载**：从 `%APPDATA%/ca410_reader/config.json` 读取 JSON，仅接受 DEFAULTS 中存在的键（白名单过滤）。

**保存**：写入 JSON，自动创建目录，静默忽略错误。

### 7.2 TestCase 加载器

`load_test_cases(filepath) → list[TestCase]`

- 打开 Excel "测试用例" 工作表
- 从第 3 行开始迭代
- 解析字段：test_id(列1), image_mode(列2), peak_brightness(列3), backlight_value(列4), local_dimming(列5), window_size(列6, 去除%), hdr_sdr(列7), window_brightness(列8), note(列12)
- `_parse_percent`：去除 `%` 后缀后转浮点数

### 7.3 Excel 导出器

`export_to_excel(data: list[dict], filepath: str) → tuple[int, int]`

**匹配键** (`MATCH_KEYS`)：`['图像模式', '峰值亮度', '当前背光值', 'Local Dimming', '小窗口大小', 'HDR/SDR', '白块亮度(nit)']`

**归一化算法** (`_norm`)：

1. `str(val).strip()`
2. 去除末尾 `%`
3. 尝试 `float()` 转换：若为整数则转为整数字符串（`"100.0"` → `"100"`）
4. `.lower()`

**匹配流程**：

1. `_find_match_row`：遍历第 3 行起，按 7 个键归一化比较
2. `_write_to_row`：写入 Lv/x/y，居中对齐，数字格式 Lv=`0.00`，x/y=`0.0000`
3. 无匹配 → `_ensure_extra_sheet` + `_append_extra`：写入"额外数据"工作表

### 7.4 测试方案管理

**加载**：`load_profile(filepath) → TestProfile`

- JSON → TestProfile，`TestStep` 列表
- 名称默认为文件名 stem

**默认值继承** (`TestStep.resolved`)：

- 将 `self` 的非 None 字段覆盖 `defaults` 字典
- 返回合并后的完整参数字典

**_DEFAULTS**：

| 键 | 默认值 | 说明 |
|----|--------|------|
| `timing` | 34 | 3840×2160@60Hz |
| `color_space` | 0 | RGB(0-255) |
| `color_depth` | 1 | 10bit |
| `pattern` | 26 | Window 图案 |
| `hdr` | 0 | SDR |
| `bt2020` | 0 | 关 |
| `ire` | 255 | 满白 |
| `window_size` | 100 | 100% |

**其他函数**：

- `list_profiles(directory) → list[Path]`：扫描 `profiles/` 目录下的 `*.json`
- `save_profile(profile, filepath)`：写入 JSON，省略 None/空字段

### 7.5 CSV 导出器

`export_to_csv(data: list[dict], headers: list[str], filepath: str)`

- `DictWriter`，UTF-8-BOM（`utf-8-sig`）编码
- `extrasaction='ignore'` 忽略多余字段

### 7.6 字体检测

`_detect_fonts()`：

- 有序候选列表：CJK（10 个候选项，Windows 优先）、Mono（3 个候选项）
- 关键词扫描回退
- 模块字典缓存

---

## 8. 协议详细说明

### 8.1 CA-S40 串口协议

**命令格式**：`{CMD}\r`

**响应格式**：`OK00` 或 `ERxx`

| 命令 | 格式 | 说明 | 时序要求 |
|------|------|------|----------|
| `COM,1` | `COM,1\r` | 进入远程模式 | 后续命令等待 **500ms** |
| `COM,0` | `COM,0\r` | 退出远程模式 | - |
| `PSC,{n}` | `PSC,1\r` | 选择探头 n | 单探头机型不支持（返回 ER10），后续等待 **100ms** |
| `MDS,{n}` | `MDS,0\r` | 设置显示模式 (0=xyLv, 2=TduvLv) | 后续等待 **200ms** |
| `MES` | `MES\r` | 触发测量 | - |
| `ZRC` | `ZRC\r` | 零点校准 | 探头盖须盖上，无环境光 |

**响应解析**：

- xyLv：`OK00,P1 {x};{y};{Lv}` — x/y 省略 "0." 前缀，Lv 含小数点
- TduvLv：`OK00,P1 {Lv};{Tcp};{duv}` — 三个值均含小数点
- 探头前缀 `"P1 "` 需去除

### 8.2 Murideo 控制协议

**命令格式**：`\r\n{FUNCTION}||{CATEGORY},{VALUE}\r\n`

| 函数 | 用途 | 典型 Category |
|------|------|---------------|
| `SENDSINGLE` | 大部分设置命令 | 时序、色彩空间、色深、HDR、BT.2020 |
| `SENDDOUBLE` | 图案选择和复合音频 | 测试图案、Dolby/DTS |
| `SENDOTHER` | 特殊命令 | IRE 初始化、IRE 窗口、恢复出厂 |

**响应格式**：`RESPONSE||{32768+CATEGORY}||{VALUE}\r\n`

**偏移量**：响应 category = 命令 category + 32768

**IRE/窗口控制序列**：

1. `SENDOTHER||63739` — 初始化 IRE 模式
2. `SENDDOUBLE||98,26` — 选择 Window 图案
3. 等待 **700ms**（图案生效的必要延迟）
4. `SENDOTHER||30971,{IRE},{SIZE}` — 设置 IRE 亮度（0-255）+ 窗口大小（0-100%）

**常用 Category 速查**：

| Category | ID | 函数 | 值域 |
|----------|-----|------|------|
| TIMING | 97 | SENDSINGLE | 时序 ID（如 34=3840×2160@60Hz） |
| PATTERN | 98 | SENDDOUBLE | 图案 ID（如 26=Window, 11=White, 10=Black） |
| COLOR_SPACE | 99 | SENDSINGLE | 0=RGB(0-255), 1=RGB(16-235), 2-4=YC |
| COLOR_DEPTH | 100 | SENDSINGLE | 0=8bit, 1=10bit, 2=12bit, 3=16bit |
| HDR | 111 | SENDSINGLE | 0=SDR, 1=HDR10, 2=HLG |
| BT.2020 | 112 | SENDSINGLE | 0=关, 1=开 |
| FACTORY_RESET | 30722 | SENDOTHER | 无参数 |
| IRE_WINDOW | 30971 | SENDOTHER | {IRE},{SIZE} |
| IRE_INIT | 63739 | SENDOTHER | 无参数 |
