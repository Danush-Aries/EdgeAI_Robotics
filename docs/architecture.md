# OpenClaw – Architecture Overview

## System Topology

```
┌──────────────────────────────────┐        MQTT/TLS (8883)       ┌──────────────────────────────────┐
│         Cloud Brain              │  ─────────────────────────►  │        ESP32 Firmware            │
│  (Python 3.11+)                  │                               │  (ESP-IDF / C)                   │
│                                  │  ◄─────────────────────────   │                                  │
│  • LLM goal decomposition        │       Telemetry JSON          │  • ReAct step parser             │
│  • ReAct reasoning loop          │                               │  • Tool dispatcher               │
│  • MQTT command publisher        │                               │  • NVS config store              │
└──────────────────────────────────┘                               └──────────────────────────────────┘
              │
              │  (optional)
              ▼
      Anthropic Claude API
```

## Message Formats

### Cloud → Firmware  (`openclaw/<id>/commands`)
```json
{
  "command": "MOVE",
  "params":  { "x": 10, "y": 20, "z": 5 },
  "thought": "The blue block is at position (10, 20, 5)."
}
```

### Firmware → Cloud  (`openclaw/<id>/telemetry`)
```json
{
  "arm_pos":     { "x": 10.0, "y": 20.0, "z": 5.0 },
  "gripper":     "closed",
  "observation": "gripper_closed_ok"
}
```

## ReAct Loop

```
User goal  ──►  LLM (Claude or mock)  ──►  Step list
                                               │
                            ┌──────────────────┘
                            ▼
                  Thought: reasoning text
                  Action:  MOVE | GRIP | SENSOR | STATUS
                  Params:  { … }
                            │
                            ▼
                    send_command() ──► MQTT ──► ESP32
                            │
                            ▼ (async via on_telemetry callback)
                  Observation: telemetry from firmware
```

## Tool IDs (firmware)

| Tool            | C Enum              | Description                   |
|-----------------|---------------------|-------------------------------|
| `MOVE`          | `TOOL_MOVE_ARM`     | Move arm to (x, y, z)         |
| `GRIP`          | `TOOL_GRIPPER`      | Open or close gripper         |
| `SENSOR`        | `TOOL_READ_SENSORS` | Read proximity / force sensors |
| `STATUS`        | `TOOL_SAY_STATUS`   | Report current robot state    |
