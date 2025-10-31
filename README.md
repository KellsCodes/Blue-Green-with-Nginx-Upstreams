# Blue/Green Deployment with Nginx Auto-Failover & Slack Alerts
This project demonstrates Blue/Green deployment with automatic failover, zero downtime, and real-time alerting via Slack — all orchestrated using Nginx and Docker Compose.
It ensures uninterrupted service by automatically switching traffic to the backup (Green) pool when the primary (Blue) becomes unhealthy.

## Components
- **Blue App** 		primary service (X-App-Pool: blue)
- **Green App** 	backup service (X-App-Pool: green)
- **Nginx** 		load balancer and failover proxy handling retries and pool switching
- **Alert Watcher** 	Python service that monitors Nginx logs for errors and failover events, and sends Slack alerts

## Requirements
- Docker and Docker Compose installed
- Copy .env.example to .env

## Environment Variables (from .env)
| Variable                   | Description                           | Default                     |
| -------------------------- | ------------------------------------- | --------------------------- |
| `ACTIVE_POOL`              | Starting pool (`blue` or `green`)     | `blue`                      |
| `BLUE_IMAGE`               | Image for Blue service                |                             |
| `GREEN_IMAGE`              | Image for Green service               |                             |
| `PORT`                     | App internal port                     | `3000`                      |
| `NGINX_PORT`               | Public port for Nginx                 | `8080`                      |
| `BLUE_PORT` / `GREEN_PORT` | Direct ports                          | `8081 / 8082`               |
| `LOG_PATH`                 | Path to Nginx access log              | `/var/log/nginx/access.log` |
| `ERROR_RATE_THRESHOLD`     | Alert threshold for 5xx errors (%)    | `2`                         |
| `WINDOW_SIZE`              | Number of recent requests to track    | `200`                       |
| `ALERT_COOLDOWN_SEC`       | Cool-down period between alerts (sec) | `300`                       |
| `SLACK_WEBHOOK_URL`        | Incoming Webhook URL for Slack alerts | *(required)*                |


## Running the Stack
```bash
cp .env.example .env
docker compose up -d

- Main entrypoint:   http://<server-ip>:8080
- Blue direct port:  http://<server-ip>:8081
- Green direct port: http://<server-ip>:8082

## Testing
- Confirm Baseline:
curl -i http://<server-ip>:8080/version
***Expected Response***: 
HTTP/1.1 200 ok
X-App-Pool: blue
X-Release-Id: blue-v1

- Simulate failure:
curl -x POST http://<server-ip>:8081/chaos/start?mode=error

Then send requests again through nginx
curl -i http://<server-ip>:8080/version
***Expected Response***: 
HTTP/1.1 200 ok
X-App-Pool: green
X-Release-Id: green-v1

* Nginx automatically reroutes to Green without downtime or failed requests.
* Slack should post a "Failure detected: Blue --> Green" alert.

- Recover Blue
curl -X POST http://<server-ip>:8081/chaos/stop

After a few seconds:
curl -i http://<server-ip>:8080/version
***Expected Response***
X-App-Pool: blue

curl -X POST "http://localhost:8081/chaos/stop"

Slack should post "Recovery: Blue is healthy again" alert.

After a few seconds, Blue becomes healthy again, and traffic gradually returns to Blue:
curl -i http://localhost:8080/version

***Response***:
X-App-Pool: blue

## Testing Error-Rate Alert
If  app generates repeated 5xx responses (e.g. request /nonexistent 200+ times with>
the watcher detects > 2% 5xx errors and sends a Slack alert:
*🚨 High Error Rate Detected – 3% 5xx over last 200 requests.*

## Manual Toggle
Change ACTIVE_POOL=green in .env, then reload nginx:
```bash
docker compose restart nginx

## Notes
- Failover handled through Nginx passive health checks using:
	- max_fails=1
	- fail_timeout=5s
	- proxy_next_upstream on error, timeout, and 5xx
- Nginx forwards all app headers unchanged.
- No rebuild or redeploy needed during failover.
- No app rebuilds required.

## Logging & Alerting Details
* Custom Log Format (nginx.tmpl)
  Nginx writes structured JSON per request, including:
	* pool, release, upstream_status, upstream, request_time, upstream_response_time
* Shared Log Volume
  ./nginx-logs mounted into both Nginx and alert_watcher
* Alert Watcher (watcher.py)
  * Tails logs in real time
  * Detects pool changes and error spikes
  * Sends alerts to Slack via SLACK_WEBHOOK_URL
  * Respects cool-down to avoid spam

## Notes
* Failover handled through Nginx passive health checks using
  ax_fails=1, fail_timeout=5s, and proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504.
  http_500 http_502 http_503 http_504.
* Alerts are purely log-driven — no coupling to application logic.
* Runbook included as RUNBOOK.md for operator response steps.


*Screenshots*
1. Zero failover flip: https://res.cloudinary.com/dsosvszg7/image/upload/v1761948836/failover_detect_acpnk6.png
2. Elevated 5xx error: https://res.cloudinary.com/dsosvszg7/image/upload/v1761948836/elevated_error_bbof5n.png
3. Nginx log line snippet:
{
  "time": "2025-10-31T22:39:07+00:00",
  "client_ip": "105.116.13.8",
  "method": "GET",
  "uri": "/version",
  "pool": "green",
  "release": "green-v1",
  "upstream_status": "200",
  "upstream": "172.18.0.3:3000",
  "request_time": "0.001",
  "upstream_response_time": "0.001"
}

