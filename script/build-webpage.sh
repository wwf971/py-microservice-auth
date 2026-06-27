#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "==================================="
echo "Building Management Web Interface"
echo "==================================="
echo "Project root: $PROJECT_ROOT"
echo "Frontend dir: $FRONTEND_DIR"
echo "==================================="

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "Error: Frontend directory not found at $FRONTEND_DIR"
    exit 1
fi

cd "$FRONTEND_DIR"

# Install dependencies
echo ""
echo "Installing dependencies..."
pnpm install

# Build the React app
echo ""
echo "Building React application..."
pnpm build

# Check if build was successful
if [ -d "$FRONTEND_DIR/build" ]; then
    echo ""
    echo "==================================="
    echo "Build completed successfully!"
    echo "==================================="
    echo "Build output: $FRONTEND_DIR/build/"
    echo ""
    echo "File list:"
    ls -lh "$FRONTEND_DIR/build/"
    echo "==================================="
else
    echo ""
    echo "Build failed - no build directory found"
    exit 1
fi
