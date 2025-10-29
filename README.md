# Blue/Green Deployment with Nginx Auto-Failover

This project demonstrates Blue/Green deployment with automatic failover and manual toggle using Nginx and Docker Compose.
It ensures zero downtime by seamlessly redirecting traffic to the backup (Green) service when the primary (Blue) fails

## Components
- **Blue app** 	primary service (X-App-Pool: blue)
- **Green app** backup service (X-App-Pool: green)
- **Nginx** 	load balancer and failover proxy handling retries and switchovers

## Requirements
- Docker and Docker Compose installed
- (Optional) .env file to customize environment variables or copy .env.example to .env

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
***Response***: 
HTTP/1.1 200 ok
X-App-Pool: blue
X-Release-Id: blue-v1

- Simulate failure:
curl -x POST http://<server-ip>:8081/chaos/start?mode=error

Then send requests again through nginx
curl -i http://<server-ip>:8080/version
***Response***: 
HTTP/1.1 200 ok
X-App-Pool: green
X-Release-Id: green-v1

Nginx automatically reroutes to Green without downtime or failed requests.

- Restore Blue
curl -X POST "http://localhost:8081/chaos/stop"

After a few seconds, Blue becomes healthy again, and traffic gradually returns to Blue:
curl -i http://localhost:8080/version

***Response***:
X-App-Pool: blue

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
