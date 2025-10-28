### Decision Summary
- Implemented Nginx passive failover using `max_fails=1` and `fail_timeout=5s`.
- Chose Docker Compose for simplicity and portability.
- Used environment templating via `envsubst` and `entrypoint.sh`.


### Why Passive Health Checks
Nginx open-source doesn't provide active health checks, so failover detection uses timeouts and retry logic (`proxy_next_upstream`).


### Testing Strategy
- Used curl loops to confirm zero failed requests.
- Verified headers `X-App-Pool` and `X-Release-Id` switch appropriately.


### Improvements
Would add CI script to simulate failover automatically in future.
