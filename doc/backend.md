# Backend Design

The backend is split into three Python server processes.

## Server Types

There are two public auth server types:

- `server_grpc.py`: typed gRPC auth service.
- `server_http.py`: HTTP wrapper for browser apps and services that prefer REST.

There is also one support server:

- `server_aux.py`: config provider, management API, and management web page server.

## Process Roles

`server_aux.py` starts first. It loads config from:

```text
config/config.yaml
config/config.0.yaml
```

It exposes the composed config to other local processes through the auxiliary API.

`server_grpc.py` provides the main auth implementation. It owns user, token, and DB management RPC methods. DB-backed methods open a DB session and call the business logic in `backend/api/api.py`.

`server_http.py` provides REST endpoints. Some endpoints call the gRPC service, while login currently calls the shared business logic directly.

## Runtime Ports

Default local test ports:

- management server: `9530`
- HTTP server: `9531`
- gRPC server: `9532`
- auxiliary server: `9533`

When `PORT` is passed to the launcher, the other ports are assigned as `PORT + 1`, `PORT + 2`, and `PORT + 3`.

## Config Shape

Tracked config belongs in `config/config.yaml`.

Local secrets and local machine values belong in `config/config.0.yaml`.

The config loader normalizes YAML into the older uppercase keys still used by parts of the current backend. This keeps the refactor gradual while the runtime code is being cleaned.

## Database Dependency

The auth data source is selected by config. The service can use PostgreSQL, SQLite, or MySQL in the current DB layer.

The gRPC server should still start when a configured DB endpoint is temporarily unreachable. DB-backed methods then return an error until DB connection works. This keeps process status visible and lets the management page show DB endpoint information.

## Response Format

HTTP responses use:

```json
{ "code": 0, "data": {}, "message": "..." }
```

`code` is `0` for success. Negative values mean failure.
