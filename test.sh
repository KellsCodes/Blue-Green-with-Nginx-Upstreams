#!/bin/bash

# Target URLs
NGINX_URL="http://44.223.20.83:8080/version"
BLUE_CHAOS="http://44.223.20.83:8081/chaos/start?mode=error"
BLUE_RECOVER="http://44.223.20.83:8081/chaos/stop"

# Number of concurrent "users"
CONCURRENT=10

# Duration to simulate chaos in seconds
CHAOS_DURATION=15

echo "Step 1: Confirming baseline traffic goes to Blue..."
for i in $(seq 1 $CONCURRENT); do
  curl -s -D - $NGINX_URL -o /dev/null &
done
wait
echo "Baseline requests complete."

echo "Step 2: Triggering chaos on Blue..."
curl -s -X POST $BLUE_CHAOS
echo "Chaos started for $CHAOS_DURATION seconds."

# Simulate users sending requests continuously during chaos
end=$((SECONDS+CHAOS_DURATION))
while [ $SECONDS -lt $end ]; do
  for i in $(seq 1 $CONCURRENT); do
    curl -s -i $NGINX_URL | grep "X-App-Pool"
  done
  sleep 1
done

echo "Step 3: Stopping chaos on Blue..."
curl -s -X POST $BLUE_RECOVER
echo "Blue recovery triggered."

# Step 4: Confirm traffic returns to Blue
echo "Step 4: Confirming traffic returns to Blue..."
for i in $(seq 1 $CONCURRENT); do
  curl -s -i $NGINX_URL | grep "X-App-Pool"
done

echo "Simulation complete."
