import argparse
from awscrt import auth, io, mqtt, http
from awsiot import iotshadow
from awsiot import mqtt_connection_builder
from concurrent.futures import Future
import sys
import threading
import traceback
from uuid import uuid4

import os
import json
from dotenv import load_dotenv

import time

load_dotenv()

CERT_DIR = "./.certs/"
CLIENT_ID = os.environ.get("CLIENT_ID") or str(uuid4())
THING_NAME = os.environ.get("THING_NAME")

e = threading.Event()
mqtt_connection = None
shadow_client = None

class LockedData:
    def __init__(self):
        self.lock = threading.Lock()
        self.shadow_state = {
            "is_on": True,
            "mode": 1,
            "pattern": 1,
            "colors": []
        }

locked_data = LockedData()

# Function for gracefully quitting this sample
def exit(msg_or_exception):
    if isinstance(msg_or_exception, Exception):
        print("Exiting sample due to exception.")
        traceback.print_exception(msg_or_exception.__class__, msg_or_exception, sys.exc_info()[2])
    else:
        print("Exiting sample:", msg_or_exception)

    print("Disconnecting...")
    future = mqtt_connection.disconnect()
    future.add_done_callback(on_disconnected)

def on_disconnected(disconnect_future):
    # type: (Future) -> None
    print("Disconnected.")

    # Signal that sample is finished
    e.set()


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

if __name__ == '__main__':
    # Spin up resources
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

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
    # Note that it's not necessary to wait, commands issued to the
    # mqtt_connection before its fully connected will simply be queued.
    # But this sample waits here so it's obvious when a connection
    # fails or succeeds.
    connected_future.result()
    print("Connected!")

    try:
        # Subscribe to necessary topics.
        # Note that is **is** important to wait for "accepted/rejected" subscriptions
        # to succeed before publishing the corresponding "request".
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

        # The rest of the sample runs asyncronously.

        # Issue request for shadow's current state.
        # The response will be received by the on_get_accepted() callback
        print("Requesting current shadow state...")
        publish_get_future = shadow_client.publish_get_shadow(
            request=iotshadow.GetShadowRequest(thing_name=THING_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE)

        # Ensure that publish succeeds
        publish_get_future.result()

    except Exception as e:
        exit(e)

    e.wait()
