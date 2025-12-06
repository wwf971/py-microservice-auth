#!/bin/bash
# Development script to run all three processes locally (non-Docker)
# This mimics what supervisord does in Docker but for local development

# Don't use set -e so script doesn't exit when processes crash
set +e

# IMPORTANT: Set IS_DOCKER to false for local development
# This must be set BEFORE any config loading happens
export IS_DOCKER=false

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$PROJECT_ROOT/src"

echo "==================================="
echo "Docker Auth Service - Development"
echo "==================================="
echo "Script dir: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"
echo "IS_DOCKER: $IS_DOCKER"
echo "==================================="

# Create data directory relative to project root
DATA_DIR="$PROJECT_ROOT/data"
mkdir -p "$DATA_DIR"
echo "✓ Data directory: $DATA_DIR"

# Create logs directory
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
echo "✓ Logs directory: $LOG_DIR"

# Set Python path to include src directory
export PYTHONPATH="$SRC_DIR:$PYTHONPATH"

# Change to src directory for imports to work correctly
cd "$SRC_DIR"

echo ""
echo "Starting processes..."
echo "-----------------------------------"

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "Shutting down processes..."
    
    # Kill monitor process first
    [ -n "$MONITOR_PID" ] && kill $MONITOR_PID 2>/dev/null
    
    # Kill main processes
    [ -n "$PID_AUX" ] && kill $PID_AUX 2>/dev/null
    [ -n "$PID_GRPC" ] && kill $PID_GRPC 2>/dev/null
    [ -n "$PID_HTTP" ] && kill $PID_HTTP 2>/dev/null
    
    sleep 1
    
    # Force kill if still running
    [ -n "$PID_AUX" ] && kill -9 $PID_AUX 2>/dev/null
    [ -n "$PID_GRPC" ] && kill -9 $PID_GRPC 2>/dev/null
    [ -n "$PID_HTTP" ] && kill -9 $PID_HTTP 2>/dev/null
    
    echo "✓ All processes stopped"
    
    # Exit the script
    exit 0
}

trap cleanup INT TERM

# Start process_aux (highest priority, starts first)
echo "Starting auxiliary process..."
python "$SRC_DIR/process_aux.py" > "$LOG_DIR/process_aux.log" 2>&1 &
PID_AUX=$!
echo "✓ Auxiliary process started (PID: $PID_AUX)"
sleep 1

# Check if aux is still running
if ! kill -0 $PID_AUX 2>/dev/null; then
    echo "✗ Auxiliary process crashed! Check logs:"
    echo "  tail -f $LOG_DIR/process_aux.log"
    echo ""
    echo "Last 20 lines of log:"
    tail -20 "$LOG_DIR/process_aux.log"
    echo ""
    echo "Press Ctrl+C to exit"
    # Don't exit, just wait for user interrupt
    read -r -d '' _ </dev/tty
fi

# Wait a bit for aux to initialize
sleep 2

# Start process_grpc
echo "Starting gRPC process..."
python "$SRC_DIR/process_grpc.py" > "$LOG_DIR/process_grpc.log" 2>&1 &
PID_GRPC=$!
echo "✓ gRPC process started (PID: $PID_GRPC)"

# Start process_http
echo "Starting HTTP process..."
python "$SRC_DIR/process_http.py" > "$LOG_DIR/process_http.log" 2>&1 &
PID_HTTP=$!
echo "✓ HTTP process started (PID: $PID_HTTP)"

echo ""
echo "==================================="
echo "All processes running!"
echo "==================================="
echo "Process IDs:"
echo "  - Auxiliary: $PID_AUX"
echo "  - gRPC:      $PID_GRPC"
echo "  - HTTP:      $PID_HTTP"
echo ""
echo "Ports (from config):"
echo "  - Auxiliary/Management: 16202"
echo "  - gRPC Service:         16200"
echo "  - HTTP Service:         16201"
echo ""
echo "Logs:"
echo "  - tail -f $LOG_DIR/process_aux.log"
echo "  - tail -f $LOG_DIR/process_grpc.log"
echo "  - tail -f $LOG_DIR/process_http.log"
echo ""
echo "Management UI:"
echo "  - http://localhost:16202/manage/"
echo ""
echo "Press Ctrl+C to stop all processes"
echo "==================================="

# Monitor processes in background
(
    while true; do
        sleep 5
        
        # Check which process stopped
        if [ -n "$PID_AUX" ] && ! kill -0 $PID_AUX 2>/dev/null; then
            echo ""
            echo "⚠️  Auxiliary process (PID: $PID_AUX) has stopped!"
            echo "  Check: tail -f $LOG_DIR/process_aux.log"
            PID_AUX=""
        fi
        
        if [ -n "$PID_GRPC" ] && ! kill -0 $PID_GRPC 2>/dev/null; then
            echo ""
            echo "⚠️  gRPC process (PID: $PID_GRPC) has stopped!"
            echo "  Check: tail -f $LOG_DIR/process_grpc.log"
            PID_GRPC=""
        fi
        
        if [ -n "$PID_HTTP" ] && ! kill -0 $PID_HTTP 2>/dev/null; then
            echo ""
            echo "⚠️  HTTP process (PID: $PID_HTTP) has stopped!"
            echo "  Check: tail -f $LOG_DIR/process_http.log"
            PID_HTTP=""
        fi
    done
) &
MONITOR_PID=$!

# Wait for any child process (will be interrupted by Ctrl+C)
wait $PID_AUX $PID_GRPC $PID_HTTP $MONITOR_PID 2>/dev/null

# If we reach here, all processes stopped naturally
echo ""
echo "All processes have stopped naturally"
