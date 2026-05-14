import paho.mqtt.client as mqtt
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OpenClaw-MQTT")

class OpenClawMQTTClient:
    def __init__(self, broker, port, username, password, client_id):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id

        self.client = mqtt.Client(client_id=self.client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        logger.info(f"Connected to HiveMQ Cloud broker: {self.broker}")
        # Subscribe to command and telemetry topics
        self.client.subscribe(f"openclaw/{self.client_id}/commands")
        self.client.subscribe("openclaw/broadcast")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode()
        logger.info(f"Received message on {msg.topic}: {payload}")

        try:
            data = json.loads(payload)
            # Logic to handle commands will be integrated into the Companion Agent
            return data
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON payload")
            return None

    def connect(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Connection failed: {e}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish_telemetry(self, data):
        topic = f"openclaw/{self.client_id}/telemetry"
        payload = json.dumps(data)
        self.client.publish(topic, payload, qos=1)
        logger.info(f"Published telemetry: {payload}")

    def send_command(self, command, params=None):
        topic = f"openclaw/{self.client_id}/commands"
        payload = json.dumps({"command": command, "params": params})
        self.client.publish(topic, payload, qos=1)
        logger.info(f"Sent command {command} to {topic}")

# --- Mock C-side MQTT implementation for firmware simulation ---
# This is for documentation and a conceptual bridge
"""
// firmware/src/mqtt_layer.c (Conceptual)
#include "mqtt_client.h"

void mqtt_event_handler(void *args, esp_event_base_t base, int32_t event_id, void *event_data) {
    if (event_id == MQTT_EVENT_DATA) {
        mqtt_event_data_t *data = (mqtt_event_data_t *)event_data;
        // Route to reasoning_process_step()
        process_reasoning_step((char*)data->data, &current_step);
    }
}
"""
