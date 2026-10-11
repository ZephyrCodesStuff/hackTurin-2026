import time
import threading
from datetime import datetime, timezone
import requests
from arduino.app_utils import Bridge, App
import random
import numpy as np
from arduino.app_peripherals.camera import Camera
from arduino.app_utils.image import compress_to_jpeg

camera = Camera(resolution=(640, 480))
camera.start()

UUID = "550e8400-e29b-41d4-a716-446655440007"
BASE_URL = "https://hackturin-api.zeph.work"
EVENT_URL = f"{BASE_URL}/cameras/{UUID}/ingest"
PHOTO_URL = f"{BASE_URL}/cameras/{UUID}/photos"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlc3AzMi1yb25kbyIsImlzcyI6InRyYWZmaWMtY2FtZXJhLWFwaSIsImlhdCI6MTc5MTcxMjM4MiwiZXhwIjoxNzk0MzA0MzgyLCJhdXRob3JpemVkX2NhbWVyYV9pZHMiOlsiNTUwZTg0MDAtZTI5Yi00MWQ0LWE3MTYtNDQ2NjU1NDQwMDA3Il0sInR5cGUiOiJjYW1lcmFfdG9rZW4ifQ.rHPLCeoAaVPG6GTSU19CbJX1mxE2qKCRyqgqEXQEvXs"
HEARTBEAT_URL = f"{BASE_URL}/cameras/{UUID}/heartbeat"

COLORS = {5 : "green", 6: "amber", 7: "red"}

CUSTOM_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {JWT_TOKEN}",
    "User-Agent": UUID
}

last_event_timestamp_ms = 0

def handle_pin_trigger(pin: int):
    print(f"pin triggered: {pin}")
    if pin in COLORS.keys():
        light_change_event(COLORS[pin])
    elif pin == 8:
        crash_event();
def light_change_event(color: str):
    global last_event_timestamp_ms

    current_utc = datetime.now(timezone.utc)
    last_event_timestamp_ms = int(current_utc.timestamp() * 1000)
    formatted_date_time = current_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    print(f"Color detected : {color}")
    payload = {
         "events": [
            {
              "type": "light_change",
              "color": color,
              "timestamp": last_event_timestamp_ms
            }
          ]
        }

    try:
        response = requests.post(EVENT_URL, json=payload, headers=CUSTOM_HEADERS, timeout=5)
        print(f"Event POST status: {response.status_code}")
    except requests.exceptions.RequestException as error:
        print(f"Event POST failed: {error}")

def crash_event():
    print("crash detected")
    image: np.ndarray = camera.capture()
    imageJpeg = compress_to_jpeg(frame=image, quality=100)
    photo_id = ""
    if imageJpeg is not None:
        imageBytes = imageJpeg.tobytes()

        try:
            response = requests.post(PHOTO_URL, data=imageBytes, headers=CUSTOM_HEADERS, timeout=5)
            print(f"Event POST status foto: {response.status_code}")
            photo_id = response.json()['photo_id']
        except requests.exceptions.RequestException as error:
            print(f"Event POST failed: {error}")

    payload = {
         "events": [
            {
              "type": "crash",
              "photo_id": photo_id
            }
          ]
        }

    try:
        response = requests.post(EVENT_URL, json=payload, headers=CUSTOM_HEADERS, timeout=5)
        print(f"Event POST status: {response.status_code}")
    except requests.exceptions.RequestException as error:
        print(f"Event POST failed: {error}")
def heartbeat_worker():
    while True:
        time.sleep(5)

        heartbeat_payload = {
            "last_event_timestamp": last_event_timestamp_ms,
            "battery_level": random.randint(57, 100),
            "firmware_version": "1.0.4",
            "wifi_signal": random.randint(20, 50)
        }

        try:
            res = requests.post(HEARTBEAT_URL, json=heartbeat_payload, headers=CUSTOM_HEADERS, timeout=5)
            print(f"Sent status: {res.status_code}")
        except requests.exceptions.RequestException as err:
            print(f"Error dispatching to {HEARTBEAT_URL}: {err}")

Bridge.provide("send_post_request", handle_pin_trigger)

if __name__ == "__main__":
    print("Starting Bridge")
    heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
    heartbeat_thread.start()

    App.run()