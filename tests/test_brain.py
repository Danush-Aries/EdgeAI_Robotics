"""
Unit tests for the OpenClaw Cloud Brain.

Run with:
    cd /path/to/EdgeAI_Robotics
    python -m pytest tests/test_brain.py -v
"""

import json
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out paho-mqtt so the test can run without the package installed
# ---------------------------------------------------------------------------
paho_stub = types.ModuleType("paho")
paho_mqtt_stub = types.ModuleType("paho.mqtt")
paho_mqtt_client_stub = types.ModuleType("paho.mqtt.client")

paho_mqtt_client_stub.Client = MagicMock
paho_mqtt_client_stub.CallbackAPIVersion = MagicMock()
paho_mqtt_client_stub.CallbackAPIVersion.VERSION2 = "VERSION2"
paho_mqtt_client_stub.MQTT_ERR_SUCCESS = 0

paho_stub.mqtt = paho_mqtt_stub
paho_mqtt_stub.client = paho_mqtt_client_stub

sys.modules.setdefault("paho", paho_stub)
sys.modules.setdefault("paho.mqtt", paho_mqtt_stub)
sys.modules.setdefault("paho.mqtt.client", paho_mqtt_client_stub)

# Now we can import our modules
sys.path.insert(0, "cloud_agent")

from brain import OpenClawBrain, _llm_mock  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_brain() -> tuple["OpenClawBrain", MagicMock]:
    """Return (brain, mock_mqtt_client) for testing."""
    mock_mqtt = MagicMock()
    mock_mqtt.client_id = "OPENCLAW-TEST"
    brain = OpenClawBrain(mock_mqtt)
    return brain, mock_mqtt


# ---------------------------------------------------------------------------
# Tests: _llm_mock planner
# ---------------------------------------------------------------------------

class TestLLMMock(unittest.TestCase):
    def test_pick_up_goal_returns_two_steps(self):
        steps = _llm_mock("pick up the blue block", {})
        self.assertEqual(len(steps), 2)
        actions = [s["action"] for s in steps]
        self.assertIn("MOVE", actions)
        self.assertIn("GRIP", actions)

    def test_open_gripper_goal(self):
        steps = _llm_mock("open gripper", {})
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["action"], "GRIP")
        self.assertEqual(steps[0]["params"]["state"], "open")

    def test_home_goal_resets_position_and_gripper(self):
        steps = _llm_mock("go home", {})
        actions = [s["action"] for s in steps]
        self.assertIn("MOVE", actions)
        self.assertIn("GRIP", actions)
        move_step = next(s for s in steps if s["action"] == "MOVE")
        self.assertEqual(move_step["params"], {"x": 0, "y": 0, "z": 0})

    def test_sensor_read_goal(self):
        steps = _llm_mock("read sensor data", {})
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["action"], "SENSOR")

    def test_unknown_goal_returns_status(self):
        steps = _llm_mock("do something impossible", {})
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["action"], "STATUS")

    def test_move_step_has_xyz_params(self):
        steps = _llm_mock("pick up the blue block", {})
        move = next(s for s in steps if s["action"] == "MOVE")
        self.assertIn("x", move["params"])
        self.assertIn("y", move["params"])
        self.assertIn("z", move["params"])


# ---------------------------------------------------------------------------
# Tests: OpenClawBrain
# ---------------------------------------------------------------------------

class TestOpenClawBrain(unittest.TestCase):
    def test_plan_action_calls_send_command(self):
        brain, mock_mqtt = _make_brain()
        brain.plan_action("pick up the blue block")
        self.assertTrue(mock_mqtt.send_command.called)

    def test_plan_action_sends_move_and_grip(self):
        brain, mock_mqtt = _make_brain()
        brain.plan_action("pick up the blue block")
        calls = [c.args[0] for c in mock_mqtt.send_command.call_args_list]
        self.assertIn("MOVE", calls)
        self.assertIn("GRIP", calls)

    def test_plan_action_returns_string(self):
        brain, _ = _make_brain()
        result = brain.plan_action("pick up the blue block")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_no_duplicate_publish(self):
        """Exactly one send_command call per ReAct step; no raw string publish."""
        brain, mock_mqtt = _make_brain()
        brain.plan_action("pick up the blue block")
        # Two steps in the mock plan; exactly 2 send_command calls, no extra publishes
        self.assertEqual(mock_mqtt.send_command.call_count, 2)
        # The low-level client.publish should NOT be called directly from brain
        mock_mqtt.client.publish.assert_not_called()

    def test_update_state_merges_arm_pos(self):
        brain, _ = _make_brain()
        brain.update_state({"arm_pos": {"x": 5.0, "y": 10.0, "z": 2.0}})
        self.assertEqual(brain.state["arm_pos"]["x"], 5.0)
        self.assertEqual(brain.state["arm_pos"]["y"], 10.0)

    def test_update_state_merges_gripper(self):
        brain, _ = _make_brain()
        brain.update_state({"gripper": "closed"})
        self.assertEqual(brain.state["gripper"], "closed")

    def test_update_state_stores_observation(self):
        brain, _ = _make_brain()
        brain.update_state({"observation": "object detected at (10,20,5)"})
        self.assertEqual(brain.state["last_observation"], "object detected at (10,20,5)")

    def test_on_telemetry_callback_registered(self):
        brain, mock_mqtt = _make_brain()
        self.assertEqual(mock_mqtt.on_telemetry, brain.update_state)


# ---------------------------------------------------------------------------
# Tests: MQTT layer on_message routing
# ---------------------------------------------------------------------------

class TestMQTTLayer(unittest.TestCase):
    def setUp(self):
        from mqtt_layer import OpenClawMQTTClient  # noqa: PLC0415
        self.mqtt = OpenClawMQTTClient(
            broker="test.broker",
            port=8883,
            username="user",
            password="pass",
            client_id="TEST-001",
        )

    def test_on_telemetry_callback_called_for_telemetry_topic(self):
        callback = MagicMock()
        self.mqtt.on_telemetry = callback

        msg = MagicMock()
        msg.topic = "openclaw/TEST-001/telemetry"
        msg.payload = json.dumps({"gripper": "closed"}).encode()

        self.mqtt._on_message(None, None, msg)
        callback.assert_called_once_with({"gripper": "closed"})

    def test_non_json_message_does_not_raise(self):
        msg = MagicMock()
        msg.topic = "openclaw/TEST-001/telemetry"
        msg.payload = b"not valid json"
        # Should log a warning, not raise
        self.mqtt._on_message(None, None, msg)

    def test_broadcast_message_handled_without_crash(self):
        msg = MagicMock()
        msg.topic = "openclaw/broadcast"
        msg.payload = json.dumps({"event": "shutdown"}).encode()
        self.mqtt._on_message(None, None, msg)

    def test_send_command_publishes_json_with_thought(self):
        result_mock = MagicMock()
        result_mock.rc = 0
        self.mqtt.client.publish.return_value = result_mock

        self.mqtt.send_command("MOVE", {"x": 1, "y": 2, "z": 3}, thought="Moving to target")
        self.mqtt.client.publish.assert_called_once()
        topic, payload = self.mqtt.client.publish.call_args.args[:2]
        self.assertIn("commands", topic)
        data = json.loads(payload)
        self.assertEqual(data["command"], "MOVE")
        self.assertEqual(data["params"], {"x": 1, "y": 2, "z": 3})
        self.assertEqual(data["thought"], "Moving to target")


if __name__ == "__main__":
    unittest.main()
