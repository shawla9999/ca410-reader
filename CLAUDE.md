# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PqReadTool (CA-410 Reader) — Windows desktop app for automated display picture quality testing. Integrates a CA-410 color analyzer and Murideo Seven G8K pattern generator into a single workflow: set signal patterns → measure → record to Excel.

All UI text and error messages are in Chinese.

## Running & Building

```bash
# Run the app
python main.py

# Build Windows EXE
python -m PyInstaller CA410Reader.spec --clean --noconfirm

# Ad-hoc hardware test scripts (not a formal test suite)
python tools/test_murideo_serial.py COM3 115200
python tools/test_murideo_scan_baudrate.py COM3
python tools/test_ca410_connect.py
```

Dependencies: `pyserial>=3.5`, `websockets>=12.0`, `openpyxl>=3.0`

## Architecture

Four-layer design, strict dependency direction (top→bottom):

```
UI (tkinter panels) → Worker (thread managers) → Driver (hardware protocol) → Transport (I/O)
```

Plus a horizontal `util/` layer (config, data loading, export) used by both UI and Worker.

**Thread model**: All hardware I/O runs on daemon threads. Workers push `(msg_type, data)` tuples to a shared `queue.Queue`. The tkinter main thread polls via `root.after(100ms)`. Cancellation uses `threading.Event`.

- `MeasurementWorker` — spawns per-operation threads for CA-410; continuous mode uses a persistent thread with `stop_event.wait(interval)` between measurements
- `AutoTestWorker` — single thread runs the test loop; uses `threading.Event` for pause/advance/stop coordination; all sleep loops broken into 0.5s chunks for cooperative cancellation

**Key files**:
- `ui/main_window.py` — central orchestrator; event routing table (`_handle_result`), callback wiring, result attachment, Excel write
- `worker/auto_test_worker.py` — auto-test state machine with incremental Murideo command sending and TV param change detection
- `driver/murideo_driver.py` — reverse-engineered IRE/Window protocol (9-step batch sequence with 700ms timing constraint)

## Hardware Protocol Notes

**CA-410 (CA-S40 serial, 38400/8N1)**:
- Chromaticity values omit "0." prefix (e.g. "230" = 0.230) — handled by `_parse_chromaticity()`
- Single-probe units don't support `PSC` command (returns ER10) — caught silently
- ER10 during measurement means zero calibration needed — auto-retry with ZRC then MES

**Murideo (WebSocket preferred, Serial alternative)**:
- Command format: `\r\n{FUNC}||{CAT},{VAL}\r\n` — identical over both transports
- Response offset: response_category = command_category + 32768
- IRE/Window requires init every time (state doesn't persist): `SENDOTHER||63739` → `SENDDOUBLE||98,26` → wait 700ms → `SENDOTHER||30971,{IRE},{SIZE}`
- Serial device may echo commands — filtered by skipping lines with `||` that don't start with `RESPONSE`
- Serial port might have CA-410 connected instead — detect by `ER` prefix in response and report error

## Data Flow

- Excel write-back matches rows by 7 fields using `_norm()` comparison (strip, remove %, lowercase, float normalize)
- Test profiles: JSON with defaults + per-step overrides; `TestStep.resolved(defaults)` merges non-None fields
- Config: `%APPDATA%/ca410_reader/config.json` (whitelisted keys only)
