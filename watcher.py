import os
import json
import time
import requests
import subprocess
from collections import deque, defaultdict
from datetime import datetime

"""
Environment Variables
"""
LOG_FILE = os.getenv("LOG_PATH", "/var/log/nginx/access.log")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
ERROR_RATE_THRESHOLD = float(os.getenv("ERROR_RATE_THRESHOLD", 3))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", 10))
ALERT_COOLDOWN_SEC = int(os.getenv("ALERT_COOLDOWN_SEC", 300))
ACTIVE_POOL = os.getenv("ACTIVE_POOL", "blue")

"""
State Tracking
"""
last_alert_time = defaultdict(lambda: 0)
recent_statuses = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))
last_seen_pool = ACTIVE_POOL  # Track last pool observed in logs

"""
Helpers
"""
def wait_for_logfile(logfile):
    while not os.path.exists(logfile):
        print(f"Waiting for log file {logfile} to be created...")
        time.sleep(5)
    print(f"Log file found: {logfile}")


def follow_logs(logfile):
    """Follow logs in real-time using tail -F."""
    print(f"Watching {logfile} using tail -F ...")
    process = subprocess.Popen(
        ["tail", "-F", "-n0", logfile],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    for line in process.stdout:
        yield line.strip()


"""
Slack Notification Helpers
"""
def send_slack_message(blocks):
    if not SLACK_WEBHOOK_URL:
        print("No Slack webhook URL found in environment.")
        return

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks})
        print(f"Slack response: {response.status_code}")
    except Exception as e:
        print(f"Slack send error: {e}")


def send_startup_alert():
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "Alert Watcher activated"}},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": "*Container:*\n`alert_watcher`"},
                {"type": "mrkdwn", "text": f"*Timestamp:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"},
            ],
        },
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "🚀 Monitoring Nginx logs for failover and error-rate conditions."}]},
    ]
    send_slack_message(blocks)


def send_error_rate_alert(pool, error_count, total_count):
    error_rate = (error_count / total_count) * 100 if total_count else 0
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "⚠️  Elevated Error Rate"}},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Pool:*\n`{pool}`"},
                {"type": "mrkdwn", "text": f"*Failed Requests:*\n{error_count}/{total_count}"},
                {"type": "mrkdwn", "text": f"*Error Rate:*\n{error_rate:.1f}%"},
            ],
        },
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": f"`{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}`"},
            {"type": "mrkdwn", "text": "`alert_watcher`"},
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "Immediate investigation recommended."}]},
    ]
    send_slack_message(blocks)


def send_failover_alert(from_pool, to_pool):
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🔄 Failover Detected"}},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*From Pool:*\n`{from_pool}`"},
                {"type": "mrkdwn", "text": f"*To Pool:*\n`{to_pool}`"},
                {"type": "mrkdwn", "text": f"*Timestamp:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}`"},
            ],
        },
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "🧭 Operator Action: Check primary container health and validate upstream status."}]},
    ]
    send_slack_message(blocks)


"""
Log Line Processor
"""
def process_log_line(line):
    global last_seen_pool
    if not line:
        return

    try:
        log_data = json.loads(line)
    except json.JSONDecodeError:
        print(f"Skipping invalid JSON line: {line}")
        return

    pool = log_data.get("pool", "unknown")

    # Multi-upstream-safe parsing
    upstream_status = log_data.get("upstream_status", 200)
    if isinstance(upstream_status, str):
        try:
            status = int(upstream_status.split(",")[0].strip())
        except ValueError:
            status = 200
    else:
        status = int(upstream_status)

    # --- Failover detection ---
    if pool != last_seen_pool and pool in ("blue", "green"):
        print(f"🔄 Failover detected → {last_seen_pool} → {pool}")
        send_failover_alert(last_seen_pool, pool)
        last_seen_pool = pool

    # --- Error-rate tracking ---
    recent_statuses[pool].append(status)
    total = len(recent_statuses[pool])
    error_count = sum(1 for s in recent_statuses[pool] if s >= 500)

    print(f"Pool={pool} | Total={total} | Errors={error_count}")

    if total >= WINDOW_SIZE:
        error_rate = (error_count / total) * 100
        if error_rate >= ERROR_RATE_THRESHOLD:
            now = time.time()
            if now - last_alert_time[pool] >= ALERT_COOLDOWN_SEC:
                last_alert_time[pool] = now
                print(f"⚠️ High error rate detected for pool {pool}, sending alert…")
                send_error_rate_alert(pool, error_count, total)
            else:
                print(f"Alert for {pool} suppressed (cooldown active).")


"""
Entrypoint
"""
if __name__ == "__main__":
    print("Starting Alert Watcher (tail -F mode)…")
    print(f"LOG_FILE={LOG_FILE}")
    print(f"Threshold={ERROR_RATE_THRESHOLD}% | Window={WINDOW_SIZE} | Cooldown={ALERT_COOLDOWN_SEC}s")
    print(f"Slack webhook set = {bool(SLACK_WEBHOOK_URL)}")
    print("=========================================================")

    send_startup_alert()
    wait_for_logfile(LOG_FILE)

    for line in follow_logs(LOG_FILE):
        process_log_line(line)
