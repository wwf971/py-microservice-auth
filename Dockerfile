
FROM python:3.12-slim

# Install system dependencies including tini
RUN apt-get update && \
    apt-get install -y supervisor tini && \
    rm -rf /var/lib/apt/lists/*

# Copy source and script files directly to root-level directories
COPY src/ /src/
COPY script/ /script/

# Install Python dependencies
RUN pip install --no-cache-dir -r /src/requirements.txt

# Compile protobuf files to generate gRPC code (if proto file exists)
RUN if [ -f /src/service.proto ]; then \
    python -m grpc_tools.protoc \
        -I/src \
        --python_out=/src \
        --grpc_python_out=/src \
        /src/service.proto; \
    fi

# Make start scripts executable
RUN chmod +x /script/start.sh /script/start-dev.sh

# Create data directory
RUN mkdir -p /data && chmod 777 /data

# Create supervisor log directory
RUN mkdir -p /var/log/supervisor

# Set working directory
WORKDIR /src

# Set environment variable to indicate Docker environment
ENV IS_DOCKER=true

# Expose ports (only external-facing services)
# PORT_SERVICE_GRPC (default 16200)
EXPOSE 16200
# PORT_SERVICE_HTTP (default 16201)
EXPOSE 16201
# PORT_MANAGE (default 16202) - Management UI
EXPOSE 16202
# PORT_AUX (16203) is internal only - not exposed

# Use tini as entrypoint to handle signals properly
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run start.sh which launches supervisord
CMD ["/script/start.sh"]