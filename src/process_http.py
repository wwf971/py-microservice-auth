#!/usr/bin/env python3
"""
HTTP/Flask Service Process

This process:
1. Waits for auxiliary process to be ready
2. Fetches configuration from auxiliary process
3. Starts the Flask HTTP service
4. Handles config_update requests by terminating
"""

import logging
import os
import sys
import time
from flask import Flask, jsonify
import requests

# Add parent directory to path for imports
dir_path_current = os.path.dirname(os.path.abspath(__file__))
dir_path_third_party_global = os.path.join(dir_path_current, "third_party", "utils_python_global")
sys.path.insert(0, dir_path_current)
sys.path.insert(0, dir_path_third_party_global)

from process_aux import setup_logging
from api.api_http import register_auth_routes

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)
# Global config
current_config = None
# Create Flask app
app = Flask(__name__)


def wait_for_aux_port():
    """Wait for auxiliary process to write its port to file"""
    # Use relative path for dev, absolute for Docker
    is_docker = os.getenv('IS_DOCKER', 'true').lower() == 'true'
    if is_docker:
        data_dir = "/data"
    else:
        # Relative to project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        data_dir = os.path.join(project_root, "data")
    
    port_file = os.path.join(data_dir, "aux_port.txt")
    logger.info(f"Waiting for auxiliary process port file: {port_file}")
    
    while not os.path.exists(port_file):
        time.sleep(1)
    
    # Read port
    with open(port_file, 'r') as f:
        port = int(f.read().strip())
    
    logger.info(f"Found auxiliary process on port: {port}")
    return port


def fetch_config(aux_port: int, max_retries: int = 30):
    """
    Fetch configuration from auxiliary process
    
    Args:
        aux_port: Port of auxiliary process
        max_retries: Maximum number of retry attempts
    
    Returns:
        Configuration dictionary
    """
    url = f"http://localhost:{aux_port}/config"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                resp_data = response.json()
                if resp_data.get('code') == 0:
                    config = resp_data.get('data', {})
                    logger.info(f"Config fetched successfully ({len(config)} keys)")
                    return config
                else:
                    logger.warning(f"Failed to fetch config (attempt {attempt + 1}/{max_retries}): {resp_data.get('message')}")
            else:
                logger.warning(f"Failed to fetch config (attempt {attempt + 1}/{max_retries}): HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to fetch config (attempt {attempt + 1}/{max_retries}): {e}")
        
        time.sleep(2)
    
    raise RuntimeError(f"Failed to fetch configuration after {max_retries} attempts")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200


@app.route('/is_alive', methods=['GET'])
def is_alive():
    """Check if server is alive and return config unix_stamp_ms"""
    if current_config is None:
        return jsonify({"alive": False}), 500
    
    return jsonify({
        "alive": True,
        "unix_stamp_ms": current_config.get('unix_stamp_ms', 0)
    }), 200


@app.route('/pid', methods=['GET'])
def get_pid():
    """Return process PID"""
    return jsonify({"code": 0, "message": "ok", "data": {"pid": os.getpid()}}), 200


@app.route('/config_update', methods=['POST'])
def config_update():
    """
    Handle config update request by terminating the process.
    Supervisor will automatically restart it, and it will fetch new config.
    """
    logger.info("Received config_update request - terminating process")
    
    # Return response before exiting
    response = jsonify({"status": "ok", "message": "Restarting to apply new config"})
    
    # Schedule exit after response is sent
    def shutdown():
        time.sleep(0.5)  # Give time for response to be sent
        logger.info("Exiting process for config update...")
        os._exit(0)
    
    import threading
    threading.Thread(target=shutdown).start()
    
    return response, 200


def main():
    """Main entry point for HTTP service process"""
    global current_config
    
    logger.info("Starting HTTP service process...")
    
    # Wait for auxiliary process
    aux_port = wait_for_aux_port()
    
    # Fetch configuration
    current_config = fetch_config(aux_port)
    
    # Register authentication API routes (these call gRPC)
    register_auth_routes(app, current_config)
    
    # Get HTTP port from config
    http_port = current_config.get('PORT_SERVICE_HTTP', 16201)
    
    # Start Flask server
    logger.info(f"HTTP server starting on port {http_port}")
    app.run(host='0.0.0.0', port=http_port, debug=False)


if __name__ == '__main__':
    main()
