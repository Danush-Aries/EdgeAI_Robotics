# OpenClaw

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![C](https://img.shields.io/badge/Firmware-ESP--IDF%20C-green?logo=c)](https://docs.espressif.com/projects/esp-idf/)
[![MQTT](https://img.shields.io/badge/Transport-MQTT%20%2F%20TLS-orange)](https://mqtt.org/)

**OpenClaw** is a hybrid Edge AI robotics framework that bridges a Python cloud agent (ReAct-based reasoning loop) to an ESP32 firmware over MQTT/TLS, translating high-level natural-language goals into real-time robotic arm and gripper commands.

---

## What It Does

Most robotic systems either use hardcoded remote control or require heavy on-device models. OpenClaw takes a third path: a **hybrid reasoning architecture**.

1. **Cloud Brain (Python)** — receives a natural-language goal such as `"Pick up the blue block"`, decomposes it into a sequence of `Thought → Action` steps via a ReAct loop (optionally powered by Claude), and publishes structured JSON commands over MQTT.
2. **Edge Firmware (C / ESP32)** — does not blindly execute commands. It parses the thought-action stream, maps actions to tool IDs, enforces physical safety constraints, persists calibration data in NVS flash, and streams telemetry back to the cloud.

The two layers communicate over **MQTT with TLS** through any standard broker (HiveMQ Cloud, Mosquitto, etc.), achieving sub-100 ms command delivery with QoS 1 guarantees.

---

## Features

- **ReAct reasoning loop** — structured `Thought / Action / Observation` cycle with full auditability; every command includes the reasoning text that produced it.
- **Real LLM integration** — when `ANTHROPIC_API_KEY` is set the brain calls Claude (`claude-3-5-haiku`) to plan arbitrary goals; a built-in rule-based planner handles common goals offline with no API key required.
- **Single structured command per step** — the firmware receives exactly one JSON payload per action, eliminating the duplicate-message bug present in naive implementations.
- **Bounds-safe C parser** — the firmware's `process_reasoning_step()` uses bounded `sscanf` format strings and explicit null-termination to prevent buffer overruns.
- **Telemetry feedback loop** — firmware telemetry is routed back into the brain's state via an `on_telemetry` callback, keeping cloud and edge in sync.
- **NVS-backed configuration** — device ID, arm position, and gripper state survive power cycles via ESP32's Non-Volatile Storage.
- **Environment-variable configuration** — no credentials are hardcoded; all connection settings come from environment variables.
- **Test suite** — 18 Python unit tests (no hardware required) and 30 host-compiled C tests covering parsing, NVS, and buffer safety.

---

## Project Structure

```text
EdgeAI_Robotics/
├── cloud_agent/
│   ├── brain.py          # ReAct planning engine + LLM integration
│   └── mqtt_layer.py     # MQTT/TLS client with telemetry routing
├── firmware/
│   ├── CMakeLists.txt    # ESP-IDF project root
│   ├── sdkconfig.defaults
│   ├── include/
│   │   ├── reasoning.h   # ReAct types and tool IDs
│   │   └── nvs_manager.h # Robot config struct
│   ├── main/
│   │   └── CMakeLists.txt  # ESP-IDF component registration
│   └── src/
│       ├── main.c          # Firmware entry point
│       ├── reasoning.c     # Thought-action parser + tool dispatcher
│       └── nvs_manager.c   # NVS read/write (mock-able for host tests)
├── tests/
│   ├── test_brain.py           # Python unit tests (18 tests)
│   └── test_reasoning_host.c  # C host unit tests (30 tests)
├── docs/
│   └── architecture.md   # System topology + message formats
├── requirements.txt
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.9+
- An MQTT broker (HiveMQ Cloud free tier, or a local Mosquitto instance)
- ESP-IDF v5.x (for firmware flashing; not needed for Python-only development)

### Python Cloud Agent

```bash
# Clone the repository
git clone https://github.com/your-org/EdgeAI_Robotics.git
cd EdgeAI_Robotics

# Install dependencies
pip install -r requirements.txt

# Set connection credentials
export OPENCLAW_BROKER=your-cluster.s1.eu.hivemq.cloud
export OPENCLAW_PORT=8883
export OPENCLAW_USERNAME=your-username
export OPENCLAW_PASSWORD=your-password
export OPENCLAW_CLIENT_ID=OPENCLAW-001

# Optional: enable real LLM reasoning via Claude
export ANTHROPIC_API_KEY=sk-ant-...

# Run the brain
python3 cloud_agent/brain.py
```

### Firmware (ESP32)

```bash
# Install ESP-IDF (one-time setup)
# https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/

cd firmware

# Configure Wi-Fi and MQTT credentials via menuconfig
idf.py menuconfig

# Build and flash
idf.py build flash monitor
```

---

## Usage

### Interactive Mode

```
Goal > Pick up the blue block
[INFO] Planning action for goal: Pick up the blue block
[INFO] [Step 1] Thought: The blue block is at position (10, 20, 5)...
[INFO] [Step 1] Action : MOVE  Params: {'x': 10, 'y': 20, 'z': 5}
[INFO] Command sent  topic=openclaw/OPENCLAW-001/commands  command=MOVE
[INFO] [Step 2] Thought: Arm is now over the block. Closing the gripper...
[INFO] [Step 2] Action : GRIP  Params: {'state': 'closed'}
Result: Step 1 (MOVE): dispatched MOVE | Step 2 (GRIP): dispatched GRIP
```

### Supported Goals (built-in planner)

| Goal phrase | Steps generated |
|---|---|
| `pick up the blue block` / `pick up` | MOVE to (10, 20, 5) then GRIP close |
| `open gripper` | GRIP open |
| `go home` / `reset` | MOVE to (0, 0, 0) then GRIP open |
| `read sensor` / `sensor data` | SENSOR read |
| anything else | STATUS report |

When `ANTHROPIC_API_KEY` is set, any natural-language goal is planned by Claude.

### MQTT Command Format (Cloud to Firmware)

```json
{
  "command": "MOVE",
  "params":  { "x": 10, "y": 20, "z": 5 },
  "thought": "The blue block is at position (10, 20, 5). I must move the arm there."
}
```

### MQTT Telemetry Format (Firmware to Cloud)

```json
{
  "arm_pos":     { "x": 10.0, "y": 20.0, "z": 5.0 },
  "gripper":     "closed",
  "observation": "move_complete"
}
```

---

## Running Tests

### Python tests (no hardware or API key needed)

```bash
python3 -m pytest tests/test_brain.py -v
# 18 passed
```

### C firmware tests (host-compiled, no ESP32 needed)

```bash
cd tests
gcc -I../firmware/include \
    -o test_reasoning \
    test_reasoning_host.c \
    ../firmware/src/reasoning.c \
    ../firmware/src/nvs_manager.c
./test_reasoning
# 30 passed, 0 failed
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Cloud Brain | Python 3.9+, Paho-MQTT |
| LLM Reasoning | Anthropic Claude (optional) |
| Transport | MQTT over TLS (port 8883) |
| Broker | HiveMQ Cloud / Mosquitto |
| Firmware | C, ESP-IDF v5.x |
| State Storage | ESP32 NVS (Non-Volatile Storage) |
| Firmware Build | CMake via `idf.py` |

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for a detailed system topology diagram, message format reference, and tool-ID table.

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
