# Blue/Green Deployment with Nginx Auto-Failover

This project demonstrates Blue/Green deployment with automatic failover and manual toggle using Nginx and Docker Compose.

## Components
- **Blue app** 	(primary service)
- **Green app** (backup service)
- **Nginx** 	(load balancer and failover proxy)

## Requirements
- Docker and Docker Compose installed

## Running the Stack
```bash
cp .env.example .env
docker compose up -d

- Main entrypoint:   http://localhost:8080
- Blue direct port:  http://localhost:8081
- Green direct port: http://localhost:8082

## Testing
- Confirm baseline:
curl -i http://localhost:8080/version
***Response***: X-App-Pool: blue

- Simulate failure:
curl -x POST http://localhost:8081/chaos/start?mode=error
curl -i http://localhost:8080/version
***Response***: X-App-Pool: green

## Manual Toggle
Change ACTIVE_POOL=green in .env, then reload nginx:
```bash
docker compose restart nginx

## Notes
- Failover handled via Nginx passive checks and retries.
- No app rebuilds required.
