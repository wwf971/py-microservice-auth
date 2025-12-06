#!/bin/bash
# Entry point script for Docker container
# Launches all three processes via supervisord

set -e

echo "Starting Docker Auth Service..."

# Create necessary directories
mkdir -p /data
mkdir -p /var/log/supervisor

# Ensure /data is writable
touch /data/test_write && rm /data/test_write || {
    echo "ERROR: /data is not writable"
    exit 1
}

echo "Starting supervisord..."

# Set IS_DOCKER environment variable
export IS_DOCKER=true

# Start supervisord (it will manage all three processes)
exec supervisord -c /script/supervisord.conf
