#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANAGE_DIR="$PROJECT_ROOT/src/manage"

echo "==================================="
echo "Building Management Web Interface"
echo "==================================="
echo "Project root: $PROJECT_ROOT"
echo "Manage dir: $MANAGE_DIR"
echo "==================================="

# Check if manage directory exists
if [ ! -d "$MANAGE_DIR" ]; then
    echo "✗ Error: Manage directory not found at $MANAGE_DIR"
    exit 1
fi

# Change to manage directory
cd "$MANAGE_DIR"

# Install dependencies
echo ""
echo "Installing dependencies..."
pnpm install

# Build the React app
echo ""
echo "Building React application..."
pnpm build

# Check if build was successful
if [ -d "$MANAGE_DIR/build" ]; then
    echo ""
    echo "==================================="
    echo "✓ Build completed successfully!"
    echo "==================================="
    echo "Build output: $MANAGE_DIR/build/"
    echo ""
    echo "File list:"
    ls -lh "$MANAGE_DIR/build/"
    echo "==================================="
else
    echo ""
    echo "✗ Build failed - no build directory found"
    exit 1
fi
