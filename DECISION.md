### Decision Summary
- Implemented passive failover in Nginx using max_fails=1 and fail_timeout=5s.
- Used Docker Compose for environment consistency and portability across hosts.
- Managed configuration values dynamically via envsubst and a startup script (entrypoint.sh).


### Why Passive Health Checks
Nginx OSS does not provide active health checks; therefore, failover detection relies on:
- Tight timeouts (proxy_read_timeout, proxy_send_timeout)
- Retry policy using proxy_next_upstream on error, timeout, and 5xx responses.
This ensures fast detection and smooth switching to the backup upstream.

### Testing Strategy
- Used curl to test /version, /chaos/start, and /chaos/stop endpoints.
- Confirmed zero failed requests during simulated Blue downtime.
- Verified headers X-App-Pool and X-Release-Id were forwarded correctly and switched between Blue and Green pools.

