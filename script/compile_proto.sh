s# source ./compile_proto.sh
echo "Compiling auth.proto..."

# Capture both stdout and stderr
ERROR_OUTPUT=$(python -m grpc_tools.protoc \
    -I./src \
    --python_out=./src/proto \
    --grpc_python_out=./src/proto \
    ./src/service.proto 2>&1)

if [ $? -eq 0 ]; then
    echo "✓ Compilation succeeded. generated files:"
    echo "  - src/proto/service_pb2.py (message classes)"
    echo "  - src/proto/service_pb2_grpc.py (service classes)"
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