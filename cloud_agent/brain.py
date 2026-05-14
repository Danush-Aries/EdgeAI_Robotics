import json
import logging
import time
from mqtt_layer import OpenClawMQTTClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OpenClaw-Brain")

class OpenClawBrain:
    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client
        self.state = {
            "arm_pos": {"x": 0.0, "y": 0.0, "z": 0.0},
            "gripper": "open",
            "last_observation": ""
        }

    def plan_action(self, user_goal):
        """
        Simulates the ReAct (Reasoning and Acting) loop in the cloud.
        In a production setup, this would call the Anthropic API.
        """
        logger.info(f"Planning action for goal: {user_goal}")

        # Mocking the LLM reasoning process
        # Goal: "Pick up the blue block"
        if "blue block" in user_goal.lower():
            thought = "The blue block is at (10, 20, 5). I need to move the arm and close the gripper."
            action = "MOVE"
            params = {"x": 10, "y": 20, "z": 5}

            # First step: Move
            self.execute_step(thought, action, params)

            # Second step: Grip
            thought_2 = "Now that the arm is in position, I must secure the block."
            action_2 = "GRIP"
            params_2 = {"state": "closed"}
            self.execute_step(thought_2, action_2, params_2)

            return "Successfully orchestrated movement to pick up blue block."

        return "Goal not recognized by brain."

    def execute_step(self, thought, action, params):
        logger.info(f"Brain Thought: {thought}")
        logger.info(f"Brain Action: {action} with {params}")

        # Package the ReAct-style message for the ESP32 firmware to parse
        # Format: "Thought: ... | Action: ..."
        payload = f"Thought: {thought} | Action: {action}"

        # Send via MQTT
        self.mqtt_client.send_command(action, params)
        # We also send the raw ReAct string to test the firmware's parsing logic
        self.mqtt_client.client.publish(f"openclaw/{self.mqtt_client.client_id}/commands", payload)

    def update_state(self, telemetry_data):
        logger.info(f"Updating brain state with telemetry: {telemetry_data}")
        self.state.update(telemetry_data)

def main():
    # Configuration (Replace with real HiveMQ Cloud credentials)
    mqtt_client = OpenClawMQTTClient(
        broker="your-hivemq-cluster.smqtt.us-east-1.hivemq.cloud",
        port=8883,
        username="admin",
        password="password",
        client_id="OPENCLAW-001"
    )

    brain = OpenClawBrain(mqtt_client)
    mqtt_client.connect()

    try:
        while True:
            user_input = input("Enter goal for OpenClaw (or 'quit'): ")
            if user_input.lower() == 'quit':
                break

            result = brain.plan_action(user_input)
            print(f"Result: {result}")
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()
