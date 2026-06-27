
FROM python:3.12-slim

# Install system dependencies including tini and git
RUN apt-get update
RUN apt-get install -y supervisor
RUN apt-get install -y tini
RUN apt-get install -y git
RUN rm -rf /var/lib/apt/lists/*

# Copy backend and script files directly to root-level directories
COPY backend/ /backend/
    # backend/third_party/ will be ignored, as specificed in .dockerignore
COPY script/ /script/
COPY frontend/build/ /frontend/build/

# Install Python dependencies
RUN pip install -r /backend/requirements.txt

# Clone third-party library and checkout specific commit
RUN mkdir -p /backend/third_party && \
    cd /backend/third_party && \
    git clone https://github.com/wwf971/utils-python-global.git && \
    cd utils-python-global && \
    git checkout 9e070e9 && \
    rm -rf .git && \
    cd /backend/third_party && \
    mv utils-python-global utils_python_global


# Compile protobuf files to generate gRPC code (if proto file exists)
RUN if [ -f /backend/service.proto ]; then \
    mkdir -p /backend/proto && \
    python -m grpc_tools.protoc \
        -I/backend \
        --python_out=/backend/proto \
        --grpc_python_out=/backend/proto \
        /backend/service.proto; \
    fi

# Make start scripts executable
RUN chmod +x /script/start.sh /script/start-dev.sh

# Create data directory
RUN mkdir -p /data && chmod 777 /data

# Create supervisor log directory
RUN mkdir -p /var/log/supervisor

# Set working directory
WORKDIR /backend

# Set environment variable to indicate Docker environment
ENV IS_DOCKER=true

# Expose ports
EXPOSE 9530
EXPOSE 9531
EXPOSE 9532
EXPOSE 9533

# Use tini as entrypoint to handle signals properly
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run start.sh which launches supervisord
CMD ["/script/start.sh"]