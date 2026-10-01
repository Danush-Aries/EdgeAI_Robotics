# OpenClaw (EdgeAI_Robotics)

**Natural-language goal in. Real robot arm motion out.**

![License](https://img.shields.io/badge/License-MIT-yellow)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![ESP32](https://img.shields.io/badge/Firmware-ESP--IDF%20C-00979D?logo=espressif&logoColor=white)
![MQTT](https://img.shields.io/badge/Transport-MQTT%20%2F%20TLS-660066)
![Claude](https://img.shields.io/badge/Reasoning-Claude-D97757?logo=anthropic&logoColor=white)

OpenClaw is a hybrid Edge AI robotics stack. A Python cloud brain runs a ReAct loop that turns natural-language goals into structured actions; an ESP32 firmware in C receives them over MQTT/TLS, enforces safety limits, and drives the servos. No heavy on-device models required.

---

## Why this exists

Most hobbyist robotics is either dumb (hard-coded remote control) or over-engineered (running a full VLM on a Jetson). OpenClaw splits the load: the ESP32 handles what edges do well — real-time control, safety, sensor telemetry — and the cloud handles what LLMs do well — planning, tool selection, natural-language interfaces. The link between them is a tiny JSON protocol over MQTT, so the same firmware works with any reasoning backend.

---

## Try it in 60 seconds

```bash
git clone https://github.com/Danush-Aries/EdgeAI_Robotics
cd EdgeAI_Robotics
pip install -r requirements.txt

# MQTT broker settings (e.g. a HiveMQ Cloud cluster; TLS on 8883)
export OPENCLAW_BROKER=your-cluster.s1.eu.hivemq.cloud
export OPENCLAW_USERNAME=...   OPENCLAW_PASSWORD=...

# Optional: use Claude for planning
export ANTHROPIC_API_KEY=...

# Interactive prompt; type a goal such as "Pick up the blue block"
cd cloud_agent && python brain.py

# Firmware (ESP-IDF toolchain required)
cd ../firmware && idf.py -p /dev/ttyUSB0 flash monitor
```

No Anthropic key? A built-in rule-based planner handles a small vocabulary of goals (pick up, open gripper, home/reset, read sensor) offline. An MQTT broker is still required to publish commands.

Tests:

```bash
python -m pytest tests/test_brain.py -v
# firmware parser, host-side (no ESP32 needed)
cd tests && gcc -I../firmware/include -o test_reasoning test_reasoning_host.c ../firmware/src/reasoning.c ../firmware/src/nvs_manager.c && ./test_reasoning
```

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
|  bounded sscanf ReAct step parser             |
|  tool dispatcher                              |
|  NVS config store                             |
+-----------------------------------------------+
                  |
                  v
                servos / gripper
```

Every command includes the reasoning text that produced it — full auditability from LLM decision to physical motion.

---

## Stack

| Layer | Tech |
|---|---|
| Cloud brain | Python 3.9+, ReAct pattern |
| LLM (optional) | Claude 3.5 Haiku via Anthropic API |
| Transport | MQTT with TLS (HiveMQ / Mosquitto) |
| Firmware | ESP-IDF C on ESP32 |
| Persistence | ESP32 NVS (config store) |
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

MIT — see [LICENSE](LICENSE).
