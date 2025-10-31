#!/bin/sh

set -e

echo "Starting envsubst substitution for nginx template"

# Define the source (template) and destination (output) paths
TEMPLATE_PATH="/etc/nginx/templates/default.conf.template"
OUTPUT_PATH="/etc/nginx/conf.d/default.conf"

# Check if the template exists
if [ -f "$TEMPLATE_PATH" ]; then
	echo "Template found at $TEMPLATE_PATH"
	
	# Run envsubst to replace environment variables with their actual values
	# The command reads the template, substitutes ${VARIABLES}, and writes the result to OUTPUT_PATH
	envsubst '$ACTIVE_POOL $PORT $BLUE_PORT $GREEN_PORT $RELEASE_ID_BLUE $RELEASE_ID_GREEN' < "$TEMPLATE_PATH" > "$OUTPUT_PATH"

	echo "Substitution complete! Generated config saved to $OUTPUT_PATH"
else
	echo "Template not found at $TEMPLATE_PATH"
	exit 1
fi

# --- Ensure log files exists for watcher ---
mkdir -p /var/log/nginx
touch /var/log/nginx/access.log
touch /var/log/nginx/error.log

echo "--- Final nginx config ---"
head -n 20 "$OUTPUT_PATH"
echo "--------------------------"

echo "Starting nginx in the foreground mode..."
# Run nginx in the foreground (required for Docker containers)
nginx -g 'daemon off;'
