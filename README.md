# OpenClaw

**Natural-language goal in. Real robot arm motion out.**

<!-- hero: 1600x600 photo of the ESP32-driven arm rig executing a pick-up-block goal -->

![License](https://img.shields.io/badge/License-MIT-yellow)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![ESP32](https://img.shields.io/badge/Firmware-ESP--IDF%20C-00979D?logo=espressif&logoColor=white)
![MQTT](https://img.shields.io/badge/Transport-MQTT%20%2F%20TLS-660066)
![Claude](https://img.shields.io/badge/Reasoning-Claude-D97757?logo=anthropic&logoColor=white)

OpenClaw is a hybrid Edge AI robotics stack. A Python cloud brain runs a ReAct loop that turns natural-language goals into structured actions; an ESP32 firmware in C receives them over MQTT/TLS, enforces safety limits, and drives the servos. Sub-100ms command delivery, no heavy on-device models required.

---

## Why this exists

Most hobbyist robotics is either dumb (hard-coded remote control) or over-engineered (running a full VLM on a Jetson). OpenClaw splits the load: the ESP32 handles what edges do well — real-time control, safety, sensor telemetry — and the cloud handles what LLMs do well — planning, tool selection, natural-language interfaces. The link between them is a tiny JSON protocol over MQTT, so the same firmware works with any reasoning backend.

---

## Try it in 60 seconds

```bash
# Cloud brain
git clone https://github.com/Danush-Aries/EdgeAI_Robotics
cd EdgeAI_Robotics
pip install -r requirements.txt

# Optional: use Claude for planning
export ANTHROPIC_API_KEY=sk-ant-...

python -m cloud_agent.brain --goal "Pick up the blue block"

# Firmware (separate machine)
cd firmware && idf.py -p /dev/ttyUSB0 flash monitor
```

No Anthropic key? A built-in rule-based planner handles the common goals offline.

---

## How it works

```
                Cloud (Python)
+-----------------------------------------------+
|  ReAct loop                                   |
|    Thought  -> "arm is at rest; move to X"    |
|    Action   -> {"tool": "arm.move", ...}      |
|    Observation <- telemetry from ESP32        |
|                                               |
|  Planner: Claude 3.5 Haiku OR rule-based      |
+-----------------|-----------------------------+
                  | MQTT + TLS (QoS 1)
                  v
                Edge (ESP32 / C)
+-----------------------------------------------+
|  bounded sscanf JSON parser                   |
|  tool ID dispatcher                           |
|  physical bounds enforcement                  |
|  NVS: persist calibration + last position     |
|  telemetry publisher                          |
+-----------------------------------------------+
                  |
                  v
                servos / gripper
```

Every command includes the reasoning text that produced it — full auditability from LLM decision to physical motion.

---

## Screenshots

<!-- screenshot: react-loop.png -->
<!-- screenshot: telemetry-dashboard.png -->
<!-- photo: hardware-rig.jpg -->

---

## Stack

| Layer | Tech |
|---|---|
| Cloud brain | Python 3.9+, ReAct pattern |
| LLM (optional) | Claude 3.5 Haiku via Anthropic API |
| Transport | MQTT with TLS (HiveMQ / Mosquitto) |
| Firmware | ESP-IDF C on ESP32 |
| Persistence | ESP32 NVS (calibration, arm state) |
| Tests | pytest for brain, unit tests for parser |

---

## More from Danush

Part of a broader stack of AI + security tooling:

- [jarvis](https://github.com/Danush-Aries/jarvis) — portable multi-provider AI assistant (voice/web/CLI)
- [breachintel](https://github.com/Danush-Aries/breachintel) — OSINT breach intelligence aggregator
- [cve-advisor](https://github.com/Danush-Aries/cve-advisor) — AI-powered CVE triage and patch recommendation
- [llm-fragility-lab](https://github.com/Danush-Aries/llm-fragility-lab) — adversarial testing lab for LLM robustness
- [network-intrusion-analyzer](https://github.com/Danush-Aries/network-intrusion-analyzer) — Suricata + Claude AI intrusion triage
- [autonomous-coding-agent](https://github.com/Danush-Aries/autonomous-coding-agent) — two-agent autonomous coding system

Built by [Dhanush](https://github.com/Danush-Aries) — AI engineering + cybersecurity.

## License

MIT.
