import os
import time
import json
import requests
from collections import deque

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
ACTIVE_POOL = os.getenv("ACTIVE_POOL")
ERROR_RATE_THRESHOLD = int(os.getenv("ERROR_RATE_THRESHOLD", 2))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", 200))
ALERT_COOLDOWN_SEC = int(os.getenv("ALERT_COOLDOWN_SEC", 300))
LOG_FILE = "/var/log/nginx/access.log"


def tail_f(filename):
	"""Generator that yields new lines as they are written."""
	with open(filename, "r") as f:
		# Go to the end of the file
		f.seek(0, 2)
		while True:
			line = f.readline()
			if not line:
				time.sleep(0.1) # wait for new lines
				continue
			yield line.strip()

# Sliding window for error rate
error_window = deque(maxlen=WINDOW_SIZE)

# Track last seen pool to detect failover
last_pool = ACTIVE_POOL

# last alert times to enforce cooldown
last_failover_alert = 0
last_error_alert = 0


def process_line(line):
	global last_pool, last_failover_alert, last_error_alert

	try:
		log = json.loads(line)
	except json.JSONDecodeError:
		print(f"Skipping invalid line: {line}")
		return

	pool = log.get("pool")
	upstream_status = log.get("upstream_status")

	# Convert status to int if possible
	try:
		status_code = int(upstream_status)
	except (TypeError, ValueError):
		status_code = 0

	# Add to sliding window
	error_window.append(status_code)

	current_time = time.time()

	# ---- Failover detection ----
	if pool != last_pool:
		if current_time - last_failover_alert >= ALERT_COOLDOWN_SEC:
			send_slack_alert(f"Failover detected: {last_pool} → {pool}")
			last_failover_alert = current_time
		last_pool = pool

	# ---- Error rate detection ---
	if len(error_window) == WINDOW_SIZE:
		num_5xx = sum(1 for code in error_window if 500 <= code < 600)
		error_rate = (num_5xx / WINDOW_SIZE) * 100

		if error_rate >= ERROR_RATE_THRESHOLD:
			if current_time - last_error_alert >= ALERT_COOLDOWN_SEC:
				send_slack_alert(f"High upstream 5xx error rate: {error_rate:.2f}% over last {WINDOW_SIZE} requests")
				last_error_alert = current_time



def send_slack_alert(message):
    """Send an alert message to Slack using the webhook URL."""
    if not SLACK_WEBHOOK_URL:
        print(f"Slack webhook not configured. Alert: {message}")
        return

    payload = {"text": message}

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code != 200:
            print(f"Failed to send Slack alert: {response.text}")
    except requests.RequestException as e:
        print(f"Error sending Slack alert: {e}")



if __name__ == "__main__":
    print(f"Starting watcher on {LOG_FILE}...")
    for line in tail_f(LOG_FILE):
        process_line(line)
