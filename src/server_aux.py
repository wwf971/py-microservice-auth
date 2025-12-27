#!/usr/bin/env python3
"""
Auxiliary Server - Config Manager and Log Aggregator

This server:
1. Parses and manages config
2. Provides config to other servers via REST API
3. Accepts logs from other servers
4. Monitors and can restart other servers
"""

import logging
import os
import sys
import time
from datetime import datetime, timezone
from flask import Flask, jsonify, request, send_from_directory, redirect
import requests
import grpc as grpc_lib

# Add parent directory to path for imports
import sys, os, pathlib
dir_path_current = os.path.dirname(os.path.realpath(__file__)) + "/"
dir_path_parent = pathlib.Path(dir_path_current).parent.absolute().__str__() + "/"
sys.path += [dir_path_parent]

# Add proto directory to path for gRPC imports
dir_path_proto = dir_path_current + "proto/"
sys.path.insert(0, dir_path_proto)

# Import protobuf modules
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	import proto.service_pb2 as service_pb2
	import proto.service_pb2_grpc as service_pb2_grpc
else:
	import service_pb2
	import service_pb2_grpc

from third_party.utils_python_global import _utils_file
from config import compose_config, store_config_to_local_db
from utils import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global configuration
config_current = None

# Create two Flask apps - one for management UI, one for aux API
app_manage = Flask(__name__)  # Management UI server
app_aux = Flask(__name__)     # Auxiliary API server

def get_db_file_path():
	"""Determine database file path based on environment"""
	is_docker = os.getenv('IS_DOCKER', 'true').lower() == 'true'
	if is_docker:
		return "/data/config.db"
	else:
		return dir_path_parent + "data/config.db"


def load_config():
	"""Load and compose configuration from all sources"""
	global config_current
	
	try:
		# Log environment variable for debugging
		is_docker_env = os.getenv('IS_DOCKER', 'not-set')
		logger.info(f"IS_DOCKER environment variable: {is_docker_env}")
		
		config_data = compose_config([])
		config_current = config_data.get('config', {})
		
		# Log the actual DATABASE_SQLITE_PATH from config
		logger.info(f"DATABASE_SQLITE_PATH from config: {config_current.get('DATABASE_SQLITE_PATH', 'not-set')}")
		
		# Add unix_stamp_ms - current time in milliseconds
		config_current['unix_stamp_ms'] = int(time.time() * 1000)
		
		# Store config to database
		db_file_path = get_db_file_path()
		logger.info(f"Config database file path: {db_file_path}")
		store_config_to_local_db(config_current, db_file_path)
		
		logger.info(f"Configuration loaded successfully: {len(config_current)} keys, unix_stamp_ms={config_current['unix_stamp_ms']}")
		return config_current
	except Exception as e:
		logger.error(f"Failed to load configuration: {e}")
		raise

# === Auxiliary API Routes (app_aux) ===

@app_aux.route('/config', methods=['GET'])
def get_config():
	"""Return current configuration"""
	if config_current is None:
		return jsonify({"code": -1, "message": "Configuration not loaded", "data": None}), 500
	
	return jsonify({"code": 0, "message": "success", "data": config_current}), 200

def write_port_file(port: int):
	"""Write PORT_AUX to file so other servers can find it"""
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
	try:
		_utils_file.create_dir_for_file_path(port_file)
		with open(port_file, 'w') as f:
			f.write(str(port))
		logger.info(f"Wrote PORT_AUX={port} to {port_file}")
	except Exception as e:
		logger.error(f"Failed to write port file: {e}")
		raise


@app_aux.route('/health', methods=['GET'])
def health():
	"""Health check endpoint"""
	return jsonify({"code": 0, "message": "ok", "data": None}), 200


@app_aux.route('/pid', methods=['GET'])
def get_pid():
	"""Return process PID"""
	return jsonify({"code": 0, "message": "ok", "data": {"pid": os.getpid()}}), 200


@app_aux.route('/log', methods=['POST'])
def receive_log():
	"""Receive logs from other servers"""
	try:
		log_data = request.json
		logger.info(f"Received log from {log_data.get('source', 'unknown')}: {log_data.get('message', '')}")
		return jsonify({"code": 0, "message": "ok", "data": None}), 200
	except Exception as e:
		logger.error(f"Failed to process log: {e}")
		return jsonify({"code": -1, "message": str(e), "data": None}), 400


@app_aux.route('/trigger_update/<service>', methods=['POST'])
def trigger_update_endpoint(service: str):
	"""Endpoint to trigger config update for a service"""
	success = trigger_config_update(service)
	if success:
		return jsonify({"code": 0, "message": "ok", "data": {"service": service}}), 200
	else:
		return jsonify({"code": -1, "message": "Failed to trigger update", "data": {"service": service}}), 500


# === Management UI Routes (app_manage) ===
# Serves on PORT_MANAGE (16202) with /manage/ prefix

@app_manage.route('/manage/api/server_status/<service>', methods=['GET'])
def get_server_status(service):
	"""Get server status (port and is_alive) for a specific service"""
	try:
		if service == 'aux':
			# Aux server is always alive if this endpoint responds
			port = config_current.get('PORT_AUX', 16203)
			return jsonify({
				"code": 0,
				"message": "success",
				"data": {
					"service": service,
					"port": port,
					"is_alive": True
				}
			}), 200
		elif service in ['grpc', 'http']:
			is_alive, unix_stamp_ms = check_server_alive(service)
			
			if service == 'grpc':
				port = config_current.get('PORT_SERVICE_GRPC', 16200)
			else:
				port = config_current.get('PORT_SERVICE_HTTP', 16201)
			
			return jsonify({
				"code": 0,
				"message": "success",
				"data": {
					"service": service,
					"port": port,
					"is_alive": is_alive
				}
			}), 200
		else:
			return jsonify({
				"code": -1,
				"message": f"Invalid service: {service}",
				"data": None
			}), 400
	except Exception as e:
		logger.error(f"Error getting server status for {service}: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/config', methods=['GET'])
def get_config_endpoint():
	"""Get current configuration for management UI"""
	try:
		logger.info("Retrieved config for management UI")
		return jsonify({
			"code": 0,
			"message": "success",
			"data": {"config": config_current}
		}), 200
	except Exception as e:
		logger.error(f"Error getting config: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/config', methods=['POST'])
def update_config_endpoint():
	"""Update user configuration via management UI"""
	global config_current
	
	try:
		config_updates = request.json
		if not config_updates:
			return jsonify({
				"code": -1,
				"message": "No configuration updates provided",
				"data": None
			}), 400
		
		logger.info(f"Updating user config: {config_updates}")
		
		# Import set_config_user
		from config import set_config_user, compose_config
		
		# Update config_user layer
		set_config_user(config_updates)
		
		# Recompose config from all layers
		config_data = compose_config([])
		config_current = config_data.get('config', {})
		config_current['unix_stamp_ms'] = int(time.time() * 1000)
		
		# Store updated config to database
		db_file_path = get_db_file_path()
		store_config_to_local_db(config_current, db_file_path)
		
		logger.info(f"Configuration updated successfully: {list(config_updates.keys())}")
		
		# Trigger restart of other servers if needed (so they pick up new config)
		# This is async - servers will restart themselves
		import threading
		def restart_servers_delayed():
			time.sleep(0.5)
			check_and_restart_servers_if_needed()
		threading.Thread(target=restart_servers_delayed, daemon=True).start()
		
		return jsonify({
			"code": 0,
			"message": "Configuration updated successfully",
			"data": {"config": config_current}
		}), 200
		
	except Exception as e:
		logger.error(f"Error updating config: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/users', methods=['GET'])
def get_users():
	"""Get all users by calling gRPC service"""
	try:
		# Get gRPC port
		grpc_port = config_current.get('PORT_SERVICE_GRPC', 16200)
		
		# Call gRPC ListUsers
		channel = grpc_lib.insecure_channel(f'localhost:{grpc_port}')
		stub = service_pb2_grpc.AuthServiceStub(channel)
		
		response = stub.ListUsers(service_pb2.ListUsersRequest(), timeout=5)
		
		# Convert protobuf to JSON-serializable format
		users = []
		for user_info in response.users:
			users.append({
				"uid": user_info.uid,
				"username": user_info.username,
				"password_hash": user_info.password_hash,
				"jwt_token_ids": list(user_info.jwt_token_ids)
			})
		
		channel.close()
		
		logger.info(f"Retrieved {len(users)} users for management UI")
		return jsonify({
			"code": 0,
			"message": "success",
			"data": {"users": users}
		}), 200
		
	except Exception as e:
		logger.error(f"Error getting users: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/users', methods=['POST'])
def add_user_endpoint():
	"""Add a new user by calling gRPC service"""
	try:
		data = request.json
		username = data.get('username')
		password = data.get('password')
		
		if not username or not password:
			return jsonify({
				"code": -1,
				"message": "Username and password are required",
				"data": None
			}), 400
		
		# Get gRPC port
		grpc_port = config_current.get('PORT_SERVICE_GRPC', 16200)
		
		# Call gRPC AddUser
		channel = grpc_lib.insecure_channel(f'localhost:{grpc_port}')
		stub = service_pb2_grpc.AuthServiceStub(channel)
		
		response = stub.AddUser(
			service_pb2.AddUserRequest(username=username, password=password),
			timeout=5
		)
		
		channel.close()
		
		if response.success:
			logger.info(f"Added user '{username}' with UID {response.uid}")
			return jsonify({
				"code": 0,
				"message": response.message,
				"data": {"uid": response.uid}
			}), 200
		else:
			return jsonify({
				"code": -1,
				"message": response.message,
				"data": None
			}), 400
		
	except Exception as e:
		logger.error(f"Error adding user: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/users/<int:uid>', methods=['DELETE'])
def delete_user_endpoint(uid):
	"""Delete a user by calling gRPC service"""
	try:
		# Get gRPC port
		grpc_port = config_current.get('PORT_SERVICE_GRPC', 16200)
		
		# Call gRPC DeleteUser
		channel = grpc_lib.insecure_channel(f'localhost:{grpc_port}')
		stub = service_pb2_grpc.AuthServiceStub(channel)
		
		response = stub.DeleteUser(
			service_pb2.DeleteUserRequest(uid=uid),
			timeout=5
		)
		
		channel.close()
		
		if response.success:
			logger.info(f"Deleted user with UID {uid}")
			return jsonify({
				"code": 0,
				"message": response.message,
				"data": None
			}), 200
		else:
			return jsonify({
				"code": -1,
				"message": response.message,
				"data": None
			}), 400
		
	except Exception as e:
		logger.error(f"Error deleting user: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/tokens/issue', methods=['POST'])
def issue_jwt_token():
	"""Issue a new JWT token for a user by calling gRPC service"""
	try:
		data = request.json
		uid = data.get('uid')
		
		if uid is None:
			return jsonify({
				"code": -1,
				"message": "UID is required",
				"data": None
			}), 400
		
		# Get gRPC port
		grpc_port = config_current.get('PORT_SERVICE_GRPC', 16200)
		
		# Call gRPC IssueToken
		channel = grpc_lib.insecure_channel(f'localhost:{grpc_port}')
		stub = service_pb2_grpc.AuthServiceStub(channel)
		
		response = stub.IssueToken(
			service_pb2.IssueTokenRequest(uid=uid),
			timeout=5
		)
		
		channel.close()
		
		if response.success:
			logger.info(f"Issued token for UID {uid}")
			return jsonify({
				"code": 0,
				"message": response.message,
				"data": {
					"jti": response.jti,
					"token": response.token
				}
			}), 200
		else:
			return jsonify({
				"code": -1,
				"message": response.message,
				"data": None
			}), 400
		
	except Exception as e:
		logger.error(f"Error issuing token: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/tokens/<jti>', methods=['GET'])
def get_jwt_token(jti):
	"""Get JWT token details by JTI by calling gRPC service"""
	try:
		# Get gRPC port
		grpc_port = config_current.get('PORT_SERVICE_GRPC', 16200)
		
		# Call gRPC GetTokenInfo
		channel = grpc_lib.insecure_channel(f'localhost:{grpc_port}')
		stub = service_pb2_grpc.AuthServiceStub(channel)
		
		response = stub.GetTokenInfo(
			service_pb2.GetTokenInfoRequest(jti=jti),
			timeout=5
		)
		
		channel.close()
		
		if response.success:
			logger.info(f"Retrieved token info for JTI {jti}")
			return jsonify({
				"code": 0,
				"message": response.message,
				"data": {
					"jti": response.jti,
					"uid": response.uid,
					"token": response.token,
					"created_at": response.created_at,
					"expires_at": response.expires_at
				}
			}), 200
		else:
			return jsonify({
				"code": -1,
				"message": response.message,
				"data": None
			}), 404
		
	except Exception as e:
		logger.error(f"Error getting token: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/databases', methods=['GET'])
def get_databases():
	"""Get all database connections"""
	try:
		grpc_port = config_current.get('PORT_SERVICE_GRPC', 16200)
		
		channel = grpc_lib.insecure_channel(f'localhost:{grpc_port}')
		stub = service_pb2_grpc.AuthServiceStub(channel)
		
		response = stub.GetDatabaseList(service_pb2.GetDatabaseListRequest(), timeout=5)
		
		databases = []
		for db_info in response.databases:
			databases.append({
				"id": db_info.id,
				"name": db_info.name,
				"type": db_info.type,
				"host": db_info.host if db_info.host else None,
				"port": db_info.port if db_info.port else None,
				"database": db_info.database if db_info.database else None,
				"username": db_info.username if db_info.username else None,
				"password": db_info.password if db_info.password else None,
				"path": db_info.path if db_info.path else None,
				"is_default": db_info.is_default,
				"is_removable": db_info.is_removable
			})
		
		channel.close()
		
		return jsonify({
			"code": 0,
			"message": "success",
			"data": {
				"databases": databases,
				"current_database_id": response.current_database_id
			}
		}), 200
	except Exception as e:
		logger.error(f"Error getting databases: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/databases', methods=['POST'])
def add_database_endpoint():
	"""Add a new database connection"""
	try:
		data = request.json
		
		grpc_port = config_current.get('PORT_SERVICE_GRPC', 16200)
		channel = grpc_lib.insecure_channel(f'localhost:{grpc_port}')
		stub = service_pb2_grpc.AuthServiceStub(channel)
		
		req = service_pb2.AddDatabaseRequest(
			name=data.get('name', ''),
			type=data.get('type', ''),
			host=data.get('host', ''),
			port=data.get('port', 0),
			database=data.get('database', ''),
			username=data.get('username', ''),
			password=data.get('password', ''),
			path=data.get('path', '')
		)
		
		response = stub.AddDatabase(req, timeout=5)
		channel.close()
		
		if response.success:
			return jsonify({
				"code": 0,
				"message": response.message,
				"data": {
					"id": response.database.id,
					"name": response.database.name,
					"type": response.database.type
				}
			}), 200
		else:
			return jsonify({
				"code": -1,
				"message": response.message,
				"data": None
			}), 400
	except Exception as e:
		logger.error(f"Error adding database: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/databases/<int:db_id>', methods=['DELETE'])
def remove_database_endpoint(db_id):
	"""Remove a database connection"""
	try:
		grpc_port = config_current.get('PORT_SERVICE_GRPC', 16200)
		channel = grpc_lib.insecure_channel(f'localhost:{grpc_port}')
		stub = service_pb2_grpc.AuthServiceStub(channel)
		
		response = stub.RemoveDatabase(
			service_pb2.RemoveDatabaseRequest(db_id=db_id),
			timeout=5
		)
		
		channel.close()
		
		if response.success:
			return jsonify({
				"code": 0,
				"message": response.message,
				"data": None
			}), 200
		else:
			return jsonify({
				"code": -1,
				"message": response.message,
				"data": None
			}), 400
	except Exception as e:
		logger.error(f"Error removing database: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/databases/<int:db_id>', methods=['PUT'])
def update_database_endpoint(db_id):
	"""Update database connection details"""
	try:
		data = request.json
		
		grpc_port = config_current.get('PORT_SERVICE_GRPC', 16200)
		channel = grpc_lib.insecure_channel(f'localhost:{grpc_port}')
		stub = service_pb2_grpc.AuthServiceStub(channel)
		
		req = service_pb2.UpdateDatabaseRequest(
			db_id=db_id,
			name=data.get('name', ''),
			host=data.get('host', ''),
			port=data.get('port', 0),
			database=data.get('database', ''),
			username=data.get('username', ''),
			password=data.get('password', ''),
			path=data.get('path', '')
		)
		
		response = stub.UpdateDatabase(req, timeout=5)
		channel.close()
		
		if response.success:
			return jsonify({
				"code": 0,
				"message": response.message,
				"data": None
			}), 200
		else:
			return jsonify({
				"code": -1,
				"message": response.message,
				"data": None
			}), 400
	except Exception as e:
		logger.error(f"Error updating database: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/api/databases/switch/<int:db_id>', methods=['POST'])
def switch_database_endpoint(db_id):
	"""Switch to a different database"""
	try:
		grpc_port = config_current.get('PORT_SERVICE_GRPC', 16200)
		channel = grpc_lib.insecure_channel(f'localhost:{grpc_port}')
		stub = service_pb2_grpc.AuthServiceStub(channel)
		
		response = stub.ChangeCurrentDatabase(
			service_pb2.ChangeCurrentDatabaseRequest(db_id=db_id),
			timeout=5
		)
		
		channel.close()
		
		if response.success:
			return jsonify({
				"code": 0,
				"message": response.message,
				"data": None
			}), 200
		else:
			return jsonify({
				"code": -1,
				"message": response.message,
				"data": None
			}), 400
	except Exception as e:
		logger.error(f"Error switching database: {e}")
		return jsonify({
			"code": -1,
			"message": str(e),
			"data": None
		}), 500


@app_manage.route('/manage/login', methods=['POST'])
def manage_login():
	"""Management login endpoint"""
	try:
		data = request.json
		username = data.get('username')
		password = data.get('password')
		
		# Get management credentials from config
		manage_username = config_current.get('MANAGE_USERNAME')
		manage_password = config_current.get('MANAGE_PASSWORD')
		
		if not manage_username or not manage_password:
			return jsonify({
				"code": -1,
				"message": "Management account not found in config. Please set MANAGE_USERNAME and MANAGE_PASSWORD in config.",
				"data": None
			}), 500
		
		# Validate credentials
		if username == manage_username and password == manage_password:
			logger.info(f"✓ Management login successful for user: {username}")
			# TODO: Generate proper token instead of simple string
			token = f"mgmt_{username}_{int(time.time())}"
			
			return jsonify({
				"code": 0,
				"message": "Login successful",
				"data": {
					"token": token,
					"username": username
				}
			}), 200
		else:
			logger.warning(f"✗ Management login failed for user: {username}")
			return jsonify({
				"code": -1,
				"message": "Invalid username or password",
				"data": None
			}), 401
			
	except Exception as e:
		logger.error(f"Error in manage_login: {e}")
		return jsonify({
			"code": -2,
			"message": str(e),
			"data": None
		}), 500


# === Management UI Static File Routes (MUST be last to not intercept API routes) ===

@app_manage.route('/')
def redirect_to_manage():
	"""Redirect root to /manage/"""
	return redirect('/manage/', code=302)

@app_manage.route('/manage/')
@app_manage.route('/manage/<path:path>')
def serve_manage_ui(path='index.html'):
	"""Serve management UI built with React"""
	manage_build_dir = os.path.join(os.path.dirname(__file__), 'manage', 'build')
	try:
		return send_from_directory(manage_build_dir, path)
	except:
		# Fallback to index.html for client-side routing
		return send_from_directory(manage_build_dir, 'index.html')


# === Helper Functions ===

def check_server_alive(service: str):
	"""
	Check if a service is alive and return its config unix_stamp_ms
	
	Args:
		service: 'grpc' or 'http'
		
	Returns:
		tuple: (is_alive: bool, unix_stamp_ms: int or None)
	"""
	if service not in ['grpc', 'http']:
		logger.error(f"Invalid service: {service}")
		return False, None
	
	try:
		if service == 'grpc':
			# Call gRPC IsAlive
			port = config_current.get('PORT_SERVICE_GRPC', 16200)
			channel = grpc_lib.insecure_channel(f'localhost:{port}')
			stub = service_pb2_grpc.AuthServiceStub(channel)
			
			response = stub.IsAlive(service_pb2.IsAliveRequest(), timeout=2)
			unix_stamp_ms = response.unix_stamp_ms
			logger.info(f"{service} server is alive with unix_stamp_ms={unix_stamp_ms}")
			channel.close()
			return True, unix_stamp_ms
		else:
			# HTTP uses /is_alive endpoint
			port = config_current.get('PORT_SERVICE_HTTP', 16201)
			url = f"http://localhost:{port}/is_alive"
			response = requests.get(url, timeout=2)
			
			if response.status_code == 200:
				data = response.json()
				unix_stamp_ms = data.get('unix_stamp_ms', None)
				logger.info(f"{service} server is alive with unix_stamp_ms={unix_stamp_ms}")
				return True, unix_stamp_ms
			else:
				logger.warning(f"{service} server is_alive check failed: HTTP {response.status_code}")
				return False, None
			
	except Exception as e:
		logger.debug(f"{service} server is_alive check failed: {e}")
		return False, None


def get_service_pid(service: str):
	"""
	Get PID of a service.
	
	Args:
		service: 'grpc' or 'http'
		
	Returns:
		int: PID if successful, None otherwise
	"""
	if service not in ['grpc', 'http']:
		logger.error(f"Invalid service: {service}")
		return None
	
	try:
		if service == 'grpc':
			# Call gRPC GetPID
			port = config_current.get('PORT_SERVICE_GRPC', 16200)
			channel = grpc_lib.insecure_channel(f'localhost:{port}')
			stub = service_pb2_grpc.AuthServiceStub(channel)
			
			response = stub.GetPID(service_pb2.GetPIDRequest(), timeout=2)
			pid = response.pid
			logger.info(f"{service} PID: {pid}")
			channel.close()
			return pid
		else:
			# HTTP uses /pid endpoint
			port = config_current.get('PORT_SERVICE_HTTP', 16201)
			url = f"http://localhost:{port}/pid"
			response = requests.get(url, timeout=2)
			
			if response.status_code == 200:
				data = response.json()
				if data.get('code') == 0:
					pid = data.get('data', {}).get('pid')
					logger.info(f"{service} PID: {pid}")
					return pid
			
			return None
			
	except Exception as e:
		logger.debug(f"Error getting PID for {service}: {e}")
		return None


def trigger_config_update(service: str):
	"""
	Trigger config update for a specific service (grpc or http).
	If API call fails, wait 1 second and kill by PID.
	
	Args:
		service: 'grpc' or 'http'
	"""
	if service not in ['grpc', 'http']:
		logger.error(f"Invalid service: {service}")
		return False
	
	try:
		# Determine the port based on service
		if service == 'grpc':
			port = config_current.get('PORT_SERVICE_GRPC')
		else:
			port = config_current.get('PORT_SERVICE_HTTP')
		
		if not port:
			logger.error(f"Port not configured for {service}")
			return False
		
		# First, try to get the PID
		pid = get_service_pid(service)
		
		# Send config_update request
		url = f"http://localhost:{port}/config_update"
		response = requests.post(url, timeout=5)
		
		if response.status_code == 200:
			logger.info(f"Successfully triggered config update for {service}")
			return True
		else:
			logger.warning(f"Failed to trigger config update for {service}: {response.status_code}")
			
			# If API failed and we have PID, kill by PID
			if pid:
				logger.info(f"Waiting 1 second before killing {service} by PID...")
				time.sleep(1)
				try:
					os.kill(pid, 15)  # SIGTERM
					logger.info(f"Sent SIGTERM to {service} (PID: {pid})")
					return True
				except Exception as kill_error:
					logger.error(f"Failed to kill {service} by PID: {kill_error}")
					return False
			
			return False
			
	except Exception as e:
		logger.error(f"Error triggering config update for {service}: {e}")
		
		# Try to kill by PID as fallback
		if pid:
			logger.info(f"API call failed, waiting 1 second before killing {service} by PID...")
			time.sleep(1)
			try:
				os.kill(pid, 15)  # SIGTERM
				logger.info(f"Sent SIGTERM to {service} (PID: {pid})")
				return True
			except Exception as kill_error:
				logger.error(f"Failed to kill {service} by PID: {kill_error}")
		
		return False


def check_and_restart_servers_if_needed():
	"""
	Check if grpc/http servers are alive and verify their config timestamps.
	If timestamps don't match, kill them so supervisor can restart.
	"""
	logger.info("Checking if servers need restart due to config timestamp mismatch...")
	
	current_unix_stamp = config_current.get('unix_stamp_ms')
	
	# Check both servers
	for service in ['grpc', 'http']:
		is_alive, server_unix_stamp = check_server_alive(service)
		
		if is_alive:
			if server_unix_stamp != current_unix_stamp:
				logger.warning(
					f"{service} server has mismatched config timestamp "
					f"(server: {server_unix_stamp}, current: {current_unix_stamp}). "
					f"Triggering restart..."
				)
				trigger_config_update(service)
			else:
				logger.info(f"{service} server config timestamp matches - no restart needed")
		else:
			logger.info(f"{service} server is not yet alive - will start normally")


def main():
	"""Main entry point for auxiliary server"""
	logger.info("Starting auxiliary server...")
	
	# Load configuration
	load_config()
	
	# Get ports from config
	port_aux = config_current.get('PORT_AUX', 16203)
	port_manage = config_current.get('PORT_MANAGE', 16202)
	
	# Write port to file
	write_port_file(port_aux)
	
	# Wait a bit for servers to potentially start
	logger.info("Waiting 3 seconds for servers to initialize...")
	time.sleep(3)
	
	# Check if servers are alive and restart if timestamps don't match
	check_and_restart_servers_if_needed()
	
	# Start both Flask servers in separate threads
	import threading
	from werkzeug.serving import make_server
	
	# Create servers
	aux_server = make_server('0.0.0.0', port_aux, app_aux, threaded=True)
	manage_server = make_server('0.0.0.0', port_manage, app_manage, threaded=True)
	
	# Start auxiliary API server in thread
	aux_thread = threading.Thread(
		target=aux_server.serve_forever,
		daemon=True
	)
	aux_thread.start()
	logger.info(f"Auxiliary API server started on port {port_aux}")
	
	# Start management UI server in main thread
	logger.info(f"Management UI server starting on port {port_manage}")
	try:
		manage_server.serve_forever()
	except KeyboardInterrupt:
		logger.info("Shutting down servers...")
		aux_server.shutdown()
		manage_server.shutdown()


if __name__ == '__main__':
	main()
