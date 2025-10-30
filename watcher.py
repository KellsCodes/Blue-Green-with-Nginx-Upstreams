import os
import json
import time
import requests
from collections import deque
import subprocess

# ---------------- Config ----------------
LOG_FILE = "/var/log/nginx/access.log"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
ACTIVE_POOL = os.environ.get("ACTIVE_POOL")
ERROR_RATE_THRESHOLD = float(os.environ.get("ERROR_RATE_THRESHOLD", 2.0))  # percent
WINDOW_SIZE = int(os.environ.get("WINDOW_SIZE", 200))  # number of requests
ALERT_COOLDOWN_SEC = int(os.environ.get("ALERT_COOLDOWN_SEC", 300))  # seconds

# ---------------- State ----------------
rolling_window = deque(maxlen=WINDOW_SIZE)
last_alert_time = 0
last_pool = ACTIVE_POOL

# ---------------- Functions ----------------
def send_slack_alert(message):
    global last_alert_time
    now = time.time()
    if now - last_alert_time < ALERT_COOLDOWN_SEC:
        return  # enforce cooldown
    payload = {"text": message}
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        last_alert_time = now
        print(f"Slack alert sent: {message}")
    except Exception as e:
        print(f"Failed to send Slack alert: {e}")

def process_line(line):
    global last_pool
    try:
        log = json.loads(line)
    except json.JSONDecodeError:
        return

    upstream_status = int(log.get("upstream_status", 0))
    pool = log.get("pool", ACTIVE_POOL)

    # Detect failover
    if pool != last_pool:
        send_slack_alert(f"Failover detected: {last_pool} → {pool}")
        last_pool = pool

    # Track error rate
    rolling_window.append(upstream_status)
    if len(rolling_window) == WINDOW_SIZE:
        errors = sum(1 for s in rolling_window if 500 <= s < 600)
        error_rate = (errors / WINDOW_SIZE) * 100
        if error_rate > ERROR_RATE_THRESHOLD:
            send_slack_alert(f"High error rate: {error_rate:.2f}% over last {WINDOW_SIZE} requests")

# ---------------- Main ----------------
print(f"# Starting watcher on {LOG_FILE}...")

# Wait until log file exists
while not os.path.exists(LOG_FILE):
    print(f"Waiting for {LOG_FILE} to appear...")
    time.sleep(1)

# Tail the log file using subprocess to avoid seek() issues
proc = subprocess.Popen(
    ["tail", "-F", LOG_FILE],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

for line in proc.stdout:
    process_line(line.strip())
