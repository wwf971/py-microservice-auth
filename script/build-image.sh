#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Build from project root (so COPY paths work correctly)
echo "Building Docker image from: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Use --cache-from to reuse previous build cache (faster rebuilds during development)
docker build --cache-from docker-auth:latest -t docker-auth:latest -f Dockerfile .

echo "Build completed successfully!"