#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root for volume mount
cd "$PROJECT_ROOT"

# 运行测试容器 (--rm: 容器退出后自动删除)
echo "Running test container..."
docker run --rm \
  --name py-microservice-auth-test \
  -p 16200:16200 \
  -p 16201:16201 \
  -p 16202:16202 \
  -v "$(pwd)/data:/data" \
  py-microservice-auth:latest

# PORT_SERVICE_GRPC=16200, PORT_SERVICE_HTTP=16201, PORT_MANAGE=16202
# PORT_AUX=16203 (internal only, not exposed)
# --rm: container will be removed. but image will not be removed.
