"""
OpenClaw Cloud Brain
====================
ReAct-based (Reasoning + Acting) planning engine that translates
natural-language goals into structured MQTT commands for the ESP32 firmware.

Configuration (environment variables):
    OPENCLAW_BROKER      – HiveMQ Cloud hostname
    OPENCLAW_PORT        – MQTT TLS port (default: 8883)
    OPENCLAW_USERNAME    – MQTT username
    OPENCLAW_PASSWORD    – MQTT password
    OPENCLAW_CLIENT_ID   – Robot client identifier (default: OPENCLAW-001)
    ANTHROPIC_API_KEY    – Optional; enables real LLM reasoning via Claude.
                           When absent the built-in rule-based planner is used.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import List

from mqtt_layer import OpenClawMQTTClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("OpenClaw-Brain")


# ---------------------------------------------------------------------------
# LLM helper (real Claude API when key is present, mock otherwise)
# ---------------------------------------------------------------------------

def _call_llm(goal: str, state: dict) -> List[dict]:
    """
    Return a list of ReAct steps, each:
        {"thought": str, "action": str, "params": dict}

    Uses the Anthropic API when ANTHROPIC_API_KEY is set; otherwise falls
    back to the built-in rule-based planner so the system works offline.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return _llm_anthropic(goal, state, api_key)
    return _llm_mock(goal, state)


def _llm_anthropic(goal: str, state: dict, api_key: str) -> List[dict]:
    """Call Claude to generate a ReAct plan for the given goal."""
    try:
        import anthropic  # type: ignore

        system_prompt = (
            "You are the planning brain of a robotic arm called OpenClaw.\n"
            "Given a goal, produce a JSON array of ReAct steps.\n"
            "Each step must be a JSON object with keys:\n"
            "  thought (string) – reasoning for this step\n"
            "  action  (string) – one of MOVE | GRIP | SENSOR | STATUS\n"
            "  params  (object) – action-specific key/value pairs\n\n"
            "For MOVE supply {x, y, z} as numbers.\n"
            "For GRIP supply {state: 'open'|'closed'}.\n"
            "Reply with ONLY the JSON array, no prose."
        )
        user_msg = (
            f"Current robot state: {json.dumps(state)}\n"
            f"Goal: {goal}"
        )

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = message.content[0].text.strip()
        steps = json.loads(raw)
        logger.info("LLM returned %d step(s)", len(steps))
        return steps
    except Exception as exc:  # noqa: BLE001
        logger.warning("Anthropic call failed (%s); falling back to mock planner.", exc)
        return _llm_mock(goal, state)


def _llm_mock(goal: str, _state: dict) -> List[dict]:
    """
    Rule-based fallback planner.  Handles a small vocabulary of goals so the
    system is demonstrable without any API key.
    """
    goal_lower = goal.lower()

    if "blue block" in goal_lower or "pick up" in goal_lower:
        return [
            {
                "thought": "The blue block is at position (10, 20, 5). I must move the arm there.",
                "action": "MOVE",
                "params": {"x": 10, "y": 20, "z": 5},
            },
            {
                "thought": "Arm is now over the block. Closing the gripper to secure it.",
                "action": "GRIP",
                "params": {"state": "closed"},
            },
        ]

    if "open" in goal_lower and "gripper" in goal_lower:
        return [
            {
                "thought": "User requested gripper to open. Releasing object.",
                "action": "GRIP",
                "params": {"state": "open"},
            }
        ]

    if "home" in goal_lower or "reset" in goal_lower:
        return [
            {
                "thought": "Returning arm to home position (0, 0, 0).",
                "action": "MOVE",
                "params": {"x": 0, "y": 0, "z": 0},
            },
            {
                "thought": "Resetting gripper to open state.",
                "action": "GRIP",
                "params": {"state": "open"},
            },
        ]

    if "sensor" in goal_lower or "read" in goal_lower:
        return [
            {
                "thought": "Reading current sensor telemetry from the robot.",
                "action": "SENSOR",
                "params": {},
            }
        ]

    return [
        {
            "thought": f"I don't have a specific plan for '{goal}'. Reporting current status.",
            "action": "STATUS",
            "params": {},
        }
    ]


# ---------------------------------------------------------------------------
# Brain
# ---------------------------------------------------------------------------

class OpenClawBrain:
    def __init__(self, mqtt_client: OpenClawMQTTClient):
        self.mqtt_client = mqtt_client
        self.state: dict = {
            "arm_pos": {"x": 0.0, "y": 0.0, "z": 0.0},
            "gripper": "open",
            "last_observation": "",
        }
        # Wire telemetry updates back into brain state
        self.mqtt_client.on_telemetry = self.update_state

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan_action(self, user_goal: str) -> str:
        """
        Run the ReAct loop for the given natural-language goal.
        Returns a human-readable summary of what was executed.
        """
        logger.info("Planning action for goal: %s", user_goal)
        steps = _call_llm(user_goal, self.state)

        if not steps:
            return "No plan generated."

        observations: list[str] = []
        for i, step in enumerate(steps, start=1):
            thought = step.get("thought", "")
            action = step.get("action", "STATUS")
            params = step.get("params", {})

            logger.info("[Step %d] Thought: %s", i, thought)
            logger.info("[Step %d] Action : %s  Params: %s", i, action, params)

            observation = self._execute_step(thought, action, params)
            observations.append(f"Step {i} ({action}): {observation}")

        return " | ".join(observations)

    def update_state(self, telemetry_data: dict) -> None:
        """Merge incoming firmware telemetry into brain state."""
        logger.info("Updating brain state: %s", telemetry_data)
        if "arm_pos" in telemetry_data:
            self.state["arm_pos"].update(telemetry_data["arm_pos"])
        if "gripper" in telemetry_data:
            self.state["gripper"] = telemetry_data["gripper"]
        if "observation" in telemetry_data:
            self.state["last_observation"] = telemetry_data["observation"]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_step(self, thought: str, action: str, params: dict) -> str:
        """
        Send a single ReAct step to the firmware.
        Only one structured JSON message is published per step.
        """
        self.mqtt_client.send_command(action, params, thought=thought)
        return f"dispatched {action}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load MQTT config from environment variables with sensible defaults."""
    broker = os.environ.get("OPENCLAW_BROKER")
    if not broker:
        raise EnvironmentError(
            "OPENCLAW_BROKER environment variable is not set.\n"
            "Example: export OPENCLAW_BROKER=your-cluster.s1.eu.hivemq.cloud"
        )
    return {
        "broker": broker,
        "port": int(os.environ.get("OPENCLAW_PORT", "8883")),
        "username": os.environ.get("OPENCLAW_USERNAME", ""),
        "password": os.environ.get("OPENCLAW_PASSWORD", ""),
        "client_id": os.environ.get("OPENCLAW_CLIENT_ID", "OPENCLAW-001"),
    }


def main() -> None:
    cfg = _load_config()

    mqtt_client = OpenClawMQTTClient(
        broker=cfg["broker"],
        port=cfg["port"],
        username=cfg["username"],
        password=cfg["password"],
        client_id=cfg["client_id"],
    )

    brain = OpenClawBrain(mqtt_client)
    mqtt_client.connect()

    logger.info("OpenClaw Brain ready.  Type a goal or 'quit' to exit.")
    try:
        while True:
            user_input = input("\nGoal > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break
            result = brain.plan_action(user_input)
            print(f"Result: {result}")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        mqtt_client.disconnect()
        logger.info("OpenClaw Brain stopped.")


if __name__ == "__main__":
    main()
