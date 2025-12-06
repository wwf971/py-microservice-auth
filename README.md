# Docker Auth Service

A multi-process authentication service with gRPC/HTTP APIs and web-based management UI.

## Architecture

- **process_aux.py** - Configuration manager and management UI server
- **process_grpc.py** - gRPC authentication service
- **process_http.py** - HTTP/REST authentication service
- Supervised by `supervisord` in Docker, or `start-dev.sh` for local development

## Project Structure

```
docker-auth/
├── src/
│   ├── api/                    # API implementations (pure functions, gRPC, HTTP)
│   ├── config/                 # Configuration management (default, dev, env, arg)
│   ├── manage/                 # React.js management UI
│   ├── proto/                  # Generated protobuf files (gitignored)
│   ├── third_party/            # External dependencies (gitignored)
│   ├── service.proto           # gRPC service definition
│   ├── process_*.py            # Main process entry points
│   └── requirements.txt        # Python dependencies
├── script/
│   ├── start.sh                # Docker startup script
│   ├── start-dev.sh            # Local development startup script
│   ├── supervisord.conf        # Supervisor configuration
│   └── compile_proto.sh        # Protobuf compilation script
├── data/                       # Runtime data (config DB, auth DB)
├── logs/                       # Process logs
├── Dockerfile
├── setup.sh                    # Build and run Docker container
└── README.md
```

## Quick Start

### Local Development
```bash
./script/start-dev.sh
```

### Docker
```bash
./setup.sh
```

## Ports

- **16200** - gRPC service
- **16201** - HTTP service  
- **16202** - Management UI (http://localhost:16202/manage/)
- **16203** - Internal auxiliary API (not exposed)

## Configuration

Configuration is layered in the following priority (highest to lowest):
1. Environment variables, provided by `docker run`
2. Command-line arguments, mainly used during development
3. `./src/config/config_dev.py` (development overrides, gitignored)
4. `./src/config/config_default.py` (defaults)

The `IS_DOCKER` environment variable determines database paths automatically.
