from abc import ABC, abstractmethod
from awscrt import auth, io, mqtt, http
from awsiot import iotshadow
from awsiot import mqtt_connection_builder
from concurrent.futures import Future
from dotenv import load_dotenv
import json
import os
import random
import serial
import sys
import threading
import time
import traceback
from uuid import uuid4
from virtual import VirtualLightstick

load_dotenv()

LIGHTSTICK_ID = os.environ.get("LIGHTSTICK_ID")
NUM_PIXELS = int(os.environ.get("NUM_PIXELS"))
BAUD_RATE = int(os.environ.get("BAUD_RATE"))
SERIAL_CONN = os.environ.get("SERIAL_CONN")

CERT_DIR = "./.certs/"
CLIENT_ID = os.environ.get("CLIENT_ID") or str(uuid4())
THING_NAME = os.environ.get("THING_NAME")

ser = None
lightstick = None

mode_id = None
mode = None

mqtt_connection = None
shadow_client = None

is_done = threading.Event()

class LockedData:
    def __init__(self):
        self.lock = threading.Lock()
        self.shadow_state = {
            "is_on": False,
            "mode": 0,
            "pattern": 0,
            "colors": []
        }

locked_data = LockedData()

# Custom data type for color
class Color:
    def __init__(self, color="000000"):
        if len(color) < 6:
            color = "000000"

        self.r = int(color[0:2], 16)
        self.g = int(color[2:4], 16)
        self.b = int(color[4:], 16)

class Mode(ABC):
    @abstractmethod
    def run(self):
        pass

class NullMode(Mode):
    def run(self):
        c_r = c_g = c_b = bytearray([0] * NUM_PIXELS)

        return c_r, c_g, c_b

class BasicMode(Mode):
    def __init__(self):
        self._pattern_id = None
        self._pattern = None

    def run(self):
        self._get_pattern()

        return self._pattern.render()

    def _get_pattern(self):
        new_pattern_id = locked_data.shadow_state["pattern"]

        # If pattern has actually changed
        if new_pattern_id != self._pattern_id:
            if new_pattern_id == 1:
                self._pattern = SolidPattern()
            elif new_pattern_id == 2:
                self._pattern = DotPattern()
            elif new_pattern_id == 4:
                self._pattern = BreathePattern()
            elif new_pattern_id == 6:
                self._pattern = WavePattern()
            else:
                self._pattern = NullPattern()

            self._pattern_id = new_pattern_id

class Pattern(ABC):
    @abstractmethod
    def render(self):
        pass

    def _get_colors(self):
        return locked_data.shadow_state["colors"]

class NullPattern(Pattern):
    def render(self):
        c_r = c_g = c_b = bytearray([0] * NUM_PIXELS)

        return c_r, c_g, c_b

class SolidPattern(Pattern):
    def render(self):
        colors = self._get_colors()

        color = Color(colors[0]) if len(colors) > 0 and len(colors[0]) == 6 else Color()

        c_r = bytearray([color.r] * NUM_PIXELS)
        c_g = bytearray([color.g] * NUM_PIXELS)
        c_b = bytearray([color.b] * NUM_PIXELS)

        return c_r, c_g, c_b

class DotPattern(Pattern):
    def __init__(self):
        self._i = 0
        self._dir = 1

    def render(self):
        colors = self._get_colors()

        color = Color(colors[0]) if len(colors) > 0 and len(colors[0]) == 6 else Color()

        c_r = bytearray([0] * NUM_PIXELS)
        c_g = bytearray([0] * NUM_PIXELS)
        c_b = bytearray([0] * NUM_PIXELS)

        c_r[self._i] = color.r
        c_g[self._i] = color.g
        c_b[self._i] = color.b

        if self._i >= NUM_PIXELS - 1:
            self._dir = -1

        if self._i <= 0:
            self._dir = 1

        self._i += self._dir

        time.sleep(0.1)

        return c_r, c_g, c_b
        
class WavePattern(Pattern):
    def __init__(self):
        self._i = 0
        self._ascending = True
        
    def render(self):
        colors = self._get_colors()

        color0 = Color(colors[0]) if len(colors[0]) == 6 else Color()
        color1 = Color(colors[-1]) if len(colors[-1]) == 6 else Color()
        c_r = bytearray([color0.r] * NUM_PIXELS)
        c_g = bytearray([color0.g] * NUM_PIXELS)
        c_b = bytearray([color0.b] * NUM_PIXELS)
        
        c_r[0:self._i] = bytearray([color1.r] * self._i)
        c_g[0:self._i] = bytearray([color1.g] * self._i)
        c_b[0:self._i] = bytearray([color1.b] * self._i)
        
        if self._ascending:
            self._i += 1
        else:
            self._i -= 1

        if self._i >= NUM_PIXELS and self._ascending:
            self._ascending = False
        if self._i == 0 and not self._ascending:
            self._ascending = True

        time.sleep(0.1)

        return c_r, c_g, c_b

class BreathePattern(Pattern):
    def __init__(self):
        self._mult = 0
        self._fade_in = True

    def render(self):
        colors = self._get_colors()

        color = Color(colors[0]) if len(colors) > 0 and len(colors[0]) == 6 else Color()

        c_r = bytearray([round(color.r * self._mult)] * NUM_PIXELS)
        c_g = bytearray([round(color.g * self._mult)] * NUM_PIXELS)
        c_b = bytearray([round(color.b * self._mult)] * NUM_PIXELS)
        
        if self._fade_in:
            self._mult += 0.1
        else:
            self._mult -= 0.1
        
        if self._mult >= 1.0 and self._fade_in:
            self._mult = 1.0
            self._fade_in = False
            
        if self._mult <= 0.0 and not self._fade_in:
            self._mult = 0.0
            self._fade_in = True

        time.sleep(0.1)
        
        return c_r, c_g, c_b

# Function for gracefully quitting
def exit(msg_or_exception):
    if isinstance(msg_or_exception, Exception):
        print("Exiting due to exception.")
        traceback.print_exception(msg_or_exception.__class__, msg_or_exception, sys.exc_info()[2])
    else:
        print("Exiting:", msg_or_exception)

    print("Disconnecting...")
    future = mqtt_connection.disconnect()
    future.add_done_callback(on_disconnected)

def on_disconnected(disconnect_future):
    # type: (Future) -> None
    print("Disconnected.")
    is_done.set()

def on_get_shadow_accepted(response):
    # type: (iotshadow.GetShadowResponse) -> None
    try:
        is_update = False

        print("Finished getting initial shadow state.")

        if response.state.reported:
            print("  Shadow reported state: ", end="")
            print(json.dumps(response.state.reported))

            with locked_data.lock:
                locked_data.shadow_state = response.state.reported
        else:
            is_update = True

        if response.state.delta:
            print("  Shadow delta: ", end="")
            print(json.dumps(response.state.delta))

            with locked_data.lock:
                for p in response.state.delta:
                    locked_data.shadow_state[p] = response.state.delta[p]

            is_update = True

        if is_update:
            print("  Shadow state has changed/does not exist.")

            change_shadow_state()

    except Exception as e:
        exit(e)

def on_get_shadow_rejected(error):
    # type: (iotshadow.ErrorResponse) -> None
    if error.code == 404:
        print("Thing has no shadow document.")
        change_shadow_state()
    else:
        exit("Get request was rejected. code:{} message:'{}'".format(
            error.code, error.message))

def on_shadow_delta_updated(delta):
    # type: (iotshadow.ShadowDeltaUpdatedEvent) -> None
    try:
        print("Received shadow delta event.")
        if delta.state:
            print("  Delta reports desired values are: ", end="")
            print(json.dumps(delta.state))

            with locked_data.lock:
                for p in delta.state:
                    locked_data.shadow_state[p] = delta.state[p]

            change_shadow_state()
        else:
            print("  Delta did not report a change.")

    except Exception as e:
        exit(e)

def on_publish_update_shadow(future):
    #type: (Future) -> None
    try:
        future.result()
        print("Update request published.")
    except Exception as e:
        print("Failed to publish update request.")
        exit(e)

def on_update_shadow_accepted(response):
    # type: (iotshadow.UpdateShadowResponse) -> None
    try:
        print("Finished updating reported shadow state to: ", end="")
        print(json.dumps(response.state.reported))
    except:
        exit("Updated shadow is missing the target property.")

def on_update_shadow_rejected(error):
    # type: (iotshadow.ErrorResponse) -> None
    exit("Update request was rejected. code:{} message:'{}'".format(
        error.code, error.message))

def change_shadow_state():
    print("Updating reported shadow value.")
    reported = {}
    with locked_data.lock:
        reported = locked_data.shadow_state

    request = iotshadow.UpdateShadowRequest(
        thing_name=THING_NAME,
        state=iotshadow.ShadowState(
            reported=reported,
        )
    )
    future = shadow_client.publish_update_shadow(request, mqtt.QoS.AT_LEAST_ONCE)
    future.add_done_callback(on_publish_update_shadow)

def loop():
    global mode_id, mode

    is_on = locked_data.shadow_state["is_on"]
    new_mode_id = locked_data.shadow_state["mode"] if is_on else 0

    # If mode has actually changed
    if new_mode_id != mode_id:
        if new_mode_id == 1:
            mode = BasicMode()
        else:
            mode = NullMode()

        mode_id = new_mode_id

    c_r, c_g, c_b = mode.run()

    if ser != None:
        ser.write(c_r)
        ser.write(c_g)
        ser.write(c_b)

    if lightstick != None:
        lightstick.update(c_r, c_g, c_b)



if __name__ == "__main__":
    # ser = serial.Serial(SERIAL_CONN, BAUD_RATE)
    lightstick = VirtualLightstick(NUM_PIXELS)

    # Short delay to let serial setup properly
    time.sleep(1)

    # Spin up resources
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    # Initiate MQTT connection
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=os.environ.get("THING_ENDPOINT"),
        cert_filepath=CERT_DIR + os.environ.get("CERT_FILE"),
        pri_key_filepath=CERT_DIR + os.environ.get("PRIVATE_KEY_FILE"),
        client_bootstrap=client_bootstrap,
        ca_filepath=CERT_DIR + os.environ.get("CA_FILE"),
        client_id=CLIENT_ID,
        clean_session=False,
        keep_alive_secs=6)

    print("Connecting to {} with client ID '{}'...".format(
        os.environ.get("THING_ENDPOINT"), CLIENT_ID))

    connected_future = mqtt_connection.connect()

    shadow_client = iotshadow.IotShadowClient(mqtt_connection)

    # Wait for connection to be fully established.
    connected_future.result()
    print("Connected!")

    try:
        # Subscribe to topics: delta, update_success, update_rejected, get_success, get_rejected
        print("Subscribing to Delta events...")
        delta_subscribed_future, _ = shadow_client.subscribe_to_shadow_delta_updated_events(
            request=iotshadow.ShadowDeltaUpdatedSubscriptionRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_shadow_delta_updated)

        # Wait for subscription to succeed
        delta_subscribed_future.result()

        print("Subscribing to Update responses...")
        update_accepted_subscribed_future, _ = shadow_client.subscribe_to_update_shadow_accepted(
            request=iotshadow.UpdateShadowSubscriptionRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_update_shadow_accepted)

        update_rejected_subscribed_future, _ = shadow_client.subscribe_to_update_shadow_rejected(
            request=iotshadow.UpdateShadowSubscriptionRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_update_shadow_rejected)

        # Wait for subscriptions to succeed
        update_accepted_subscribed_future.result()
        update_rejected_subscribed_future.result()

        print("Subscribing to Get responses...")
        get_accepted_subscribed_future, _ = shadow_client.subscribe_to_get_shadow_accepted(
            request=iotshadow.GetShadowSubscriptionRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_get_shadow_accepted)

        get_rejected_subscribed_future, _ = shadow_client.subscribe_to_get_shadow_rejected(
            request=iotshadow.GetShadowSubscriptionRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_get_shadow_rejected)

        # Wait for subscriptions to succeed
        get_accepted_subscribed_future.result()
        get_rejected_subscribed_future.result()

        # Issue request for shadow's current state.
        print("Requesting current shadow state...")
        publish_get_future = shadow_client.publish_get_shadow(
            request=iotshadow.GetShadowRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE)

        # Ensure that publish succeeds
        publish_get_future.result()

        while (True):
            loop()

    except KeyboardInterrupt:
        exit("Caught KeyboardInterrupt, terminating connections")

    except Exception as e:
        exit(e)

    # Wait for everything to finish
    is_done.wait()
