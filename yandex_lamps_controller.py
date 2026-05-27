import time
import psutil
import requests

# Yandex API key required
YANDEX_TOKEN = "yandextoken"
LAMP_ID = "lampid"

URL = f"https://api.iot.yandex.net/v1.0/devices/{LAMP_ID}/actions"
HEADERS = {
    "Authorization": f"Bearer {YANDEX_TOKEN}",
    "Content-Type": "application/json"
}

def change_lamp_color(hsv_color):
    """Sends a color change command to the smart lamp via Yandex Cloud"""
    payload = {
        "actions": [{
            "type": "devices.capabilities.color_setting",
            "state": {
                "instance": "hsv",
                "value": hsv_color
            }
        }]
    }
    try:
        requests.post(URL, json=payload, headers=HEADERS, timeout=3)
    except Exception as e:
        print(f"Network error: {e}")

def monitor_pc():
    print("🤖 Monitoring system active. Tracking CPU load...")
    last_state = None  # Prevents spamming the lamp with duplicate commands

    while True:
        # Get CPU load percentage
        cpu_load = psutil.cpu_percent(interval=1)
        print(f"Current CPU Load: {cpu_load}%")

        # Light mode logic
        if cpu_load < 40:
            current_state = "CHILL"
            # Calm cyan/blue color (H: 190, S: 100, V: 100)
            color = {"hsv": {"h": 190, "s": 100, "v": 100}}
        elif 40 <= cpu_load < 70:
            current_state = "WORK"
            # Yellow color for medium load (H: 60, S: 100, V: 100)
            color = {"hsv": {"h": 60, "s": 100, "v": 100}}
        else:
            current_state = "TURBO"
            # Bright red for high load (H: 0, S: 100, V: 100)
            color = {"hsv": {"h": 0, "s": 100, "v": 100}}

        # Update lamp color only if the state has changed
        if current_state != last_state:
            print(f"🔊 Changing lighting mode to: {current_state}")
            change_lamp_color(color["hsv"])
            last_state = current_state

        # Check every 5 seconds to reduce network traffic
        time.sleep(5)

if __name__ == "__main__":
    monitor_pc()
