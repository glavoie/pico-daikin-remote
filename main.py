import json
import network
import machine
import ubinascii
import time

from machine import Pin
from umqtt.robust import MQTTClient
from daikinremote import RemoteException, blast_state

from config import SSID, PASSWORD, MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, NAME

led = Pin("LED")
led.value(0)

wlan = network.WLAN(network.STA_IF)

DEFAULT_STATE = {
    "power": "off",
    "mode": "off",
    "fan_mode": "Auto",
    "temperature": "21.0",
}
CURRENT_STATE = {}

ID_PREFIX = "pico-daikin-remote"
UNIQUE_ID = ID_PREFIX + "_" + ubinascii.hexlify(machine.unique_id()).decode("utf-8")

print("Unique ID: " + UNIQUE_ID)

c = MQTTClient(UNIQUE_ID, MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASSWORD)

MQTT_TOPIC_PREFIX = b"glavoie84/" + UNIQUE_ID

MQTT_FAN_MODE_COMMAND_TOPIC = MQTT_TOPIC_PREFIX + b"/fan_mode/set"
MQTT_FAN_MODE_STATE_TOPIC = MQTT_TOPIC_PREFIX + b"/fan_mode"
MQTT_MODE_COMMAND_TOPIC = MQTT_TOPIC_PREFIX + b"/mode/set"
MQTT_MODE_STATE_TOPIC = MQTT_TOPIC_PREFIX + b"/mode"
MQTT_TEMPERATURE_COMMAND_TOPIC = MQTT_TOPIC_PREFIX + b"/temperature/set"
MQTT_TEMPERATURE_STATE_TOPIC = MQTT_TOPIC_PREFIX + b"/temperature"
MQTT_DISCOVERY_TOPIC = b"homeassistant/climate/" + UNIQUE_ID + b"/config"

def get_hass_device():
    return {
        "unique_id": UNIQUE_ID,
        "name": "Daikin IR Remote",
        "fan_mode_command_topic": MQTT_FAN_MODE_COMMAND_TOPIC,
        "fan_mode_state_topic": MQTT_FAN_MODE_STATE_TOPIC,
        "fan_modes": ["Auto", "Quiet", "1", "2", "3", "4", "5"],
        "mode_command_topic": MQTT_MODE_COMMAND_TOPIC,
        "mode_state_topic": MQTT_MODE_STATE_TOPIC,
        "modes": ["auto", "off", "cool", "heat", "dry", "fan_only"],
        "max_temp": 32,
        "min_temp": 10,
        "precision": 1,
        "temperature_command_topic": MQTT_TEMPERATURE_COMMAND_TOPIC,
        "temperature_state_topic": MQTT_TEMPERATURE_STATE_TOPIC,
        "temperature_unit": "C",
        "device": {
            "identifiers": [UNIQUE_ID],
            "name": NAME,
            "model": "pico-daikin-remote",
            "manufacturer": "glavoie84",
        }
    }


def connect_to_network():
    print("Connecting to Network (timeout 10 seconds)...")
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    # Wait for connect or fail
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        time.sleep(1)

    # Handle connection error
    if wlan.status() != 3:
        process_failed_network(wlan.status())
    else:
        blink_led(2)

        status = wlan.ifconfig()
        print("Network online! IP: " + status[0])


def process_failed_network(wlan_status):
    blink_led(3)
    raise Exception("Network connection failed: " + str(wlan_status))


def blink_led(times):
    for i in range(times):
        led.value(1)
        time.sleep_ms(250)
        led.value(0)
        time.sleep_ms(250)


def save_state():
    global CURRENT_STATE

    # Save state to JSON encoded file
    with open("state.json", "w") as f:
        json.dump(CURRENT_STATE, f)

    print("Saved state: " + str(CURRENT_STATE))


def load_state():
    # Load state from JSON encoded file, check if file exists before.
    global CURRENT_STATE

    device = get_hass_device()

    try:
        with open("state.json", "r") as f:
            loaded_state = json.load(f)

            # Check if loaded state is valid
            if loaded_state["power"] not in ["on", "off"]:
                loaded_state["power"] = DEFAULT_STATE["power"]
            CURRENT_STATE["power"] = loaded_state["power"]

            if loaded_state["mode"] not in device["modes"]:
                loaded_state["mode"] = DEFAULT_STATE["mode"]
            CURRENT_STATE["mode"] = loaded_state["mode"]

            if loaded_state["fan_mode"] not in device["fan_modes"]:
                loaded_state["fan_mode"] = DEFAULT_STATE["fan_mode"]
            CURRENT_STATE["fan_mode"] = loaded_state["fan_mode"]

            if (
                int(float(loaded_state["temperature"])) < device["min_temp"]
                or int(float(loaded_state["temperature"])) > device["max_temp"]
            ):
                loaded_state["temperature"] = DEFAULT_STATE["temperature"]
            CURRENT_STATE["temperature"] = loaded_state["temperature"]

            print("Loaded state: " + str(CURRENT_STATE))
    except Exception as e:
        print("Error while loading state, resetting to default: " + str(e))
        # Copy default state values into the current state
        CURRENT_STATE['power'] = DEFAULT_STATE['power']
        CURRENT_STATE['mode'] = DEFAULT_STATE['mode']
        CURRENT_STATE['fan_mode'] = DEFAULT_STATE['fan_mode']
        CURRENT_STATE['temperature'] = DEFAULT_STATE['temperature']


def start_mqtt_client():
    print("Starting MQTT client...")

    c.connect()

    print("Publishing device discovery message to MQTT...")
    c.publish(MQTT_DISCOVERY_TOPIC, json.dumps(get_hass_device()), True)

    time.sleep(1)

    print("Publishing current state to MQTT topics...")
    c.publish(MQTT_FAN_MODE_STATE_TOPIC, CURRENT_STATE["fan_mode"], True)
    c.publish(MQTT_FAN_MODE_COMMAND_TOPIC, CURRENT_STATE["fan_mode"])
    c.publish(MQTT_MODE_STATE_TOPIC, CURRENT_STATE["mode"], True)
    c.publish(MQTT_MODE_COMMAND_TOPIC, CURRENT_STATE["mode"])
    c.publish(MQTT_TEMPERATURE_STATE_TOPIC, CURRENT_STATE["temperature"], True)
    c.publish(MQTT_TEMPERATURE_COMMAND_TOPIC, CURRENT_STATE["temperature"])

    print("Subscribing to MQTT topics...")
    c.set_callback(process_message)
    c.subscribe(MQTT_FAN_MODE_COMMAND_TOPIC)
    c.subscribe(MQTT_MODE_COMMAND_TOPIC)
    c.subscribe(MQTT_TEMPERATURE_COMMAND_TOPIC)

    print("MQTT client started!")

def close_mqtt_client():
    print("Closing MQTT client...")
    c.disconnect()

def process_message(topic, msg):
    global CURRENT_STATE

    print("Received message: " + str(topic) + " " + str(msg))

    if topic == MQTT_FAN_MODE_COMMAND_TOPIC:
        CURRENT_STATE["fan_mode"] = msg.decode("utf-8")
        c.publish(MQTT_FAN_MODE_STATE_TOPIC, msg, True)
    elif topic == MQTT_MODE_COMMAND_TOPIC:
        CURRENT_STATE["mode"] = msg.decode("utf-8")
        c.publish(MQTT_MODE_STATE_TOPIC, msg, True)

        if CURRENT_STATE["mode"] == "off":
            CURRENT_STATE["power"] = "off"
        else:
            CURRENT_STATE["power"] = "on"
    elif topic == MQTT_TEMPERATURE_COMMAND_TOPIC:
        CURRENT_STATE["temperature"] = msg.decode("utf-8")
        c.publish(MQTT_TEMPERATURE_STATE_TOPIC, msg, True)
    else:
        print("Unknown topic...")

    try:
        blast_state(
            CURRENT_STATE["power"],
            CURRENT_STATE["mode"],
            CURRENT_STATE["temperature"],
            CURRENT_STATE["fan_mode"]
        )

        save_state()
    except RemoteException as e:
        print("Error while sending state through IR: " + str(e))


def main():
    try:
        load_state()

        connect_to_network()

        start_mqtt_client()

        while True:
            time.sleep_ms(100)

            # Process MQTT message
            c.check_msg()

            # Validate WiFi status
            if wlan.status() != 3:
                process_failed_network(wlan.status())
    except Exception as e:
        print("Fatal error: " + str(e))
        print("Sleeping 10 seconds then resetting!")
        time.sleep(10)
        machine.reset()
    except KeyboardInterrupt:
        print("Keyboard interrupt, exiting...")
        close_mqtt_client()

main()
