# auth-jwt

`auth-jwt` is a small authentication and authorization service for projects that need shared login.

It provides:

- username and password login
- JWT token issue and verification
- user management page
- built-in and service-scoped permission checks
- HTTP and gRPC APIs
- local test launch and Docker launch

## Quick Start

Local test server:

```bash
./launch.sh test
```

Then open:

```text
http://localhost:9530/manage/
```

The local test server uses these ports:

```text
9530 management page
9531 HTTP API
9532 gRPC API
9533 internal auxiliary API
```

If these ports are occupied, the test launcher frees them before starting the new test server.

## Docker

Build image:

```bash
bash ./script/build-image.sh
```

Run container:

```bash
bash ./script/run-container.sh
```

Docker uses the same default port range:

```text
9530 management page
9531 HTTP API
9532 gRPC API
9533 internal auxiliary API
```

## Project Layout

```text
auth-jwt/
  backend/     Python servers, API code, gRPC proto, management frontend
  config/      Runtime config files
  database/    Initial database schema
  doc/         Internal docs
  script/      Build and launch scripts
```

## Internal Docs

This README is for people visiting the repository.

For developer and AI-agent oriented docs, start with:

```text
doc/auth-jwt.md
```

For authorization and permission details:

```text
doc/authorization.md
```
