#!/bin/bash
# Usage: ./compile_proto.sh [--conda_env_name ENV_NAME]
# Example: ./compile_proto.sh --conda_env_name wwf

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Change to project root (parent of script directory)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Working directory: $PROJECT_ROOT"
echo ""

# Parse arguments
CONDA_ENV_NAME=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --conda_env_name)
            CONDA_ENV_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./compile_proto.sh [--conda_env_name ENV_NAME]"
            exit 1
            ;;
    esac
done

echo "Compiling auth.proto..."

# Prepare Python command
PYTHON_CMD="python"

# If conda environment is specified, activate it
if [ -n "$CONDA_ENV_NAME" ]; then
    echo "Using conda environment: $CONDA_ENV_NAME"
    
    # Check if conda is available
    if ! command -v conda &> /dev/null; then
        echo "✗ Error: conda command not found"
        exit 1
    fi
    
    # Get conda base path
    CONDA_BASE=$(conda info --base)
    
    # Source conda.sh to enable conda activate
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    
    # Activate the environment
    if ! conda activate "$CONDA_ENV_NAME" 2>/dev/null; then
        echo "✗ Error: Failed to activate conda environment '$CONDA_ENV_NAME'"
        echo "Available environments:"
        conda env list
        exit 1
    fi
    
    echo "✓ Activated conda environment: $CONDA_ENV_NAME"
    
    # Use python from activated environment
    PYTHON_CMD="python"
fi

# Capture both stdout and stderr
ERROR_OUTPUT=$($PYTHON_CMD -m grpc_tools.protoc \
    -I./src \
    --python_out=./src/proto \
    --grpc_python_out=./src/proto \
    ./src/service.proto 2>&1)

if [ $? -eq 0 ]; then
    echo "✓ Compilation succeeded. Generated files:"
    echo "  - src/proto/service_pb2.py (message classes)"
    echo "  - src/proto/service_pb2_grpc.py (service classes)"
    echo ""
    echo "Python used: $($PYTHON_CMD --version 2>&1)"
    $PYTHON_CMD -c "import google.protobuf; print(f'Protobuf version: {google.protobuf.__version__}')" 2>/dev/null || true
else
    echo "✗ Compilation failed"
    
    # Check if error is due to missing package
    if echo "$ERROR_OUTPUT" | grep -q "ModuleNotFoundError\|No module named"; then
        echo ""
        echo "Missing package detected. Please install required packages:"
        echo "  pip install grpcio-tools"
    else
        # Print the actual error
        echo ""
        echo "Error details:"
        echo "$ERROR_OUTPUT"
    fi
fi