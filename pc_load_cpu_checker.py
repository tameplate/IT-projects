import time
import psutil
from plyer import notification
# pip install plyer needed

def send_alert(cpu_load):
    """Displays a custom Windows system notification"""
    notification.notify(
        title="⚠️ CPU OVERLOAD!",
        message=f"CPU load spiked to {cpu_load}%.\nThink, Mark, think! Kill some processes!",
        app_name="PC Monitor",
        timeout=5  # How many seconds the notification stays on screen
    )


def monitor_pc():
    print("🤖 Monitor active. Watching CPU load locally...")

    # Counter to track continuous high load
    high_load_counter = 0

    while True:
        cpu_load = psutil.cpu_percent(interval=1)

        if cpu_load > 80:
            high_load_counter += 1
            print(f"🔥 Alert! CPU Load: {cpu_load}% ({high_load_counter} sec)")
        else:
            # Reset counter if load drops below the threshold
            high_load_counter = 0

        # If high load persists for 5 seconds or more — trigger the alert
        if high_load_counter >= 5:
            send_alert(cpu_load)
            # Sleep for a minute to prevent notification spamming
            time.sleep(60)
            high_load_counter = 0

        time.sleep(2)


if __name__ == "__main__":
    monitor_pc()
