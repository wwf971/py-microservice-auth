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
  --name auth-jwt-test \
  -p 9530:9530 \
  -p 9531:9531 \
  -p 9532:9532 \
  -p 9533:9533 \
  -v "$(pwd)/data:/data" \
  auth-jwt:latest

# PORT_MANAGE=9530, PORT_SERVICE_HTTP=9531, PORT_SERVICE_GRPC=9532
# PORT_AUX=9533
# --rm: container will be removed. but image will not be removed.
