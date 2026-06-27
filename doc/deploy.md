# Deploy

## Local Test Server

Start local test server:

```bash
./launch.sh test
```

Or from the common launcher:

```bash
launch-dev auth
```

Default local endpoints:

- management page: `http://localhost:9530/manage/`
- HTTP auth API: `http://localhost:9531`
- gRPC auth API: `localhost:9532`
- auxiliary API: `localhost:9533`

The management console account comes from `config/config.yaml` plus local override `config/config.0.yaml`.

## Local Config

Tracked default config:

```text
config/config.yaml
```

Local override config:

```text
config/config.0.yaml
```

Use `config/config.0.yaml` for local DB endpoint, username, password, and local manage account.

## Docker Image Build

The Docker image build fetches one helper library from GitHub:

```text
https://github.com/wwf971/utils-python-global.git
```

The Dockerfile checks out commit `9e070e9` and places it under:

```text
/backend/third_party/utils_python_global
```

The backend imports this helper package for small shared utilities such as `Dict` and file helpers. This means building the image requires GitHub network access. Raspi deployment builds the image first, then copies the built image to the Raspi, so the Raspi itself does not need to clone this repository during deployment.

## Port Rule

When `PORT` is `9530`, server ports are:

- management server: `9530`
- HTTP server: `9531`
- gRPC server: `9532`
- auxiliary server: `9533`

If a different `PORT` is passed to `launch.sh test --port`, the other ports are assigned by adding `1`, `2`, and `3`.
