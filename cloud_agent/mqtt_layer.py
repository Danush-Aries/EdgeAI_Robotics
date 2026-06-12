"""
OpenClaw MQTT Layer
===================
Wraps paho-mqtt with TLS support and topic routing for the OpenClaw system.

Topics
------
  openclaw/<client_id>/commands   – Cloud -> Firmware (JSON commands)
  openclaw/<client_id>/telemetry  – Firmware -> Cloud  (JSON telemetry)
  openclaw/broadcast              – System-wide announcements
"""

from __future__ import annotations

import json
import logging
import ssl
from typing import Optional

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("OpenClaw-MQTT")


class OpenClawMQTTClient:
    def __init__(
        self,
        broker: str,
        port: int,
        username: str,
        password: str,
        client_id: str,
    ) -> None:
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id

        # Callback registered by the Brain to receive parsed telemetry.
        # Signature: on_telemetry(data: dict) -> None
        self.on_telemetry = None

        self.client = mqtt.Client(
            client_id=self.client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self.client.username_pw_set(self.username, self.password)

        # Enable TLS (required by HiveMQ Cloud and most managed brokers).
        self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            logger.info("Connecting to broker %s:%d as %s", self.broker, self.port, self.client_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Connection failed: %s", exc)
            raise

    def disconnect(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from broker.")

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def send_command(self, command: str, params: Optional[dict] = None, thought: str = "") -> None:
        """
        Publish a single structured JSON command to the firmware.

        The payload format understood by the ESP32 firmware:
            {
                "command": "MOVE",
                "params":  {"x": 10, "y": 20, "z": 5},
                "thought": "Reasoning text for auditability"
            }
        """
        topic = f"openclaw/{self.client_id}/commands"
        payload = json.dumps(
            {
                "command": command,
                "params": params or {},
                "thought": thought,
            }
        )
        result = self.client.publish(topic, payload, qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning("publish returned rc=%d for topic %s", result.rc, topic)
        else:
            logger.info("Command sent  topic=%s  command=%s  params=%s", topic, command, params)

    def publish_telemetry(self, data: dict) -> None:
        """Publish a telemetry payload (used by firmware-side simulators / tests)."""
        topic = f"openclaw/{self.client_id}/telemetry"
        payload = json.dumps(data)
        self.client.publish(topic, payload, qos=1)
        logger.info("Telemetry published: %s", payload)

    # ------------------------------------------------------------------
    # Internal callbacks
    # ------------------------------------------------------------------

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code == 0:
            logger.info("Connected to broker %s", self.broker)
            # Subscribe to telemetry coming from the firmware
            telemetry_topic = f"openclaw/{self.client_id}/telemetry"
            broadcast_topic = "openclaw/broadcast"
            client.subscribe([(telemetry_topic, 1), (broadcast_topic, 0)])
            logger.info("Subscribed to %s and %s", telemetry_topic, broadcast_topic)
        else:
            logger.error("Connection refused, reason code: %s", reason_code)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        logger.warning("Disconnected from broker (rc=%s)", reason_code)

    def _on_message(self, client, userdata, msg) -> None:
        """
        Route incoming messages to the appropriate handler.
        Parsed telemetry is forwarded to the Brain via the on_telemetry callback
        instead of being silently discarded.
        """
        raw = msg.payload.decode(errors="replace")
        logger.info("Received  topic=%s  payload=%s", msg.topic, raw)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Non-JSON message on %s: %s", msg.topic, raw)
            return

        if "telemetry" in msg.topic:
            if callable(self.on_telemetry):
                try:
                    self.on_telemetry(data)
                except Exception as exc:  # noqa: BLE001
                    logger.error("on_telemetry callback raised: %s", exc)
            else:
                logger.debug("No on_telemetry handler registered; ignoring payload.")

        elif "broadcast" in msg.topic:
            logger.info("Broadcast message: %s", data)
