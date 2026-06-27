# API

`auth-jwt` exposes both HTTP and gRPC APIs.

Use HTTP when integrating browser apps or simple services. Use gRPC when another backend service wants typed RPC calls.

## User Login And Token Issue

HTTP:

```text
POST /api/token
POST /api/login
```

Request:

```json
{
  "username": "alice",
  "password": "password"
}
```

Success response:

```json
{
  "code": 0,
  "message": "Login successful",
  "data": {
    "token": "<jwt-token>",
    "expires_at": 1780000000,
    "username": "alice"
  }
}
```

gRPC:

```text
AuthService.Login(LoginRequest)
```

This checks username and password, creates a signed JWT token, stores token metadata in DB, and returns the long-lived `token`. `/api/login` is kept as the old route. New browser integrations should prefer `/api/token`.

## Token Verification

HTTP:

```text
POST /api/verify_jwt_token
```

Request:

```json
{
  "session_token": "<jwt-token>"
}
```

Success response:

```json
{
  "code": 0,
  "message": "Session is valid",
  "data": {
    "valid": true,
    "username": "alice"
  }
}
```

gRPC:

```text
AuthService.ValidateSession(ValidateSessionRequest)
```

This verifies token signature and expiration. The internal verification path also checks whether the token id has been revoked.

## Temporary Token

HTTP:

```text
POST /api/temporary-token
POST /api/issue_temp_token
```

Request:

```json
{
  "token": "<stored-token>"
}
```

Success response:

```json
{
  "code": 0,
  "message": "Temporary token issued",
  "data": {
    "token": "<temporary-token>",
    "expires_at": 1780000000
  }
}
```

gRPC:

```text
AuthService.IssueTempToken(IssueTempTokenRequest)
```

The source token must be a valid stored token. A temporary token cannot be used to issue another temporary token. `/api/issue_temp_token` is kept as the old route. New browser integrations should prefer `/api/temporary-token`.

## Public Keys

HTTP:

```text
GET /.well-known/jwks.json
GET /api/jwks
```

gRPC:

```text
AuthService.GetJwks(GetJwksRequest)
```

Other services use the JWKS response to verify token signatures locally.

## Public Access Through Nginx

When this service is exposed through nginx or CloudFront, expose only the routes needed by browser apps:

```text
POST /auth/api/token
POST /auth/api/temporary-token
POST /auth/api/logout
GET  /auth/.well-known/jwks.json
```

These public routes should proxy to the HTTP API server on port `9531`.

Do not expose management routes through nginx:

```text
/manage/
/manage/api/
```

The management console should stay LAN-only through `http://192.168.1.32:9530/manage/`.

## Logout

HTTP:

```text
POST /api/logout
```

gRPC:

```text
AuthService.Logout(LogoutRequest)
```

Logout revokes the stored token used in the request.

## Management APIs

The management UI uses APIs under `/manage/api`.

User management:

```text
GET    /manage/api/users
POST   /manage/api/users
PUT    /manage/api/users/<uid>/permissions
DELETE /manage/api/users/<uid>
```

User management APIs require built-in auth permissions. For example, listing users requires user read permission, creating users requires user create permission, editing permission assignments requires user edit permission, and deleting users requires user delete permission.

Token management:

```text
POST /manage/api/tokens/issue
GET  /manage/api/tokens/<jti>
POST /manage/api/tokens/<jti>/revoke
DELETE /manage/api/tokens/<jti>
POST /manage/api/tokens/cleanup
```

Token issue, read, revoke, delete, and cleanup each have their own built-in permission code. Token manage permission includes all of them.

Permission metadata:

```text
GET  /manage/api/permissions
POST /manage/api/service_permissions
```

`/manage/api/service_permissions` declares a permission code for an external service. It does not assign that permission to a service account. Permission assignments belong to users.

DB endpoint management:

```text
GET    /manage/api/databases
POST   /manage/api/databases
PUT    /manage/api/databases/<db_id>
DELETE /manage/api/databases/<db_id>
POST   /manage/api/databases/<db_id>/test
POST   /manage/api/databases/switch/<db_id>
```

Server status:

```text
GET /manage/api/server_status/aux
GET /manage/api/server_status/grpc
GET /manage/api/server_status/http
```

## Shared Sign-In Process

Login:

1. App sends username and password to `/api/token`.
2. Auth service returns a long-lived `token`.
3. App stores the `token` as sign-in state.

Temporary token:

1. Before accessing another service, the app sends the stored `token` to `/api/temporary-token`.
2. Auth service returns a short-lived `temporary token`.
3. App sends the temporary token to the service it is accessing.

Request verification:

1. Service backend receives a request with a temporary token.
2. Service backend verifies the temporary token with JWKS, or calls the internal `/api/verify_jwt_token` or gRPC `ValidateSession`.
3. If the action needs authorization, the service backend checks whether the user has the needed built-in or service-scoped permission.
4. If authentication or authorization fails, the request is rejected.

Token issue from management page:

1. Operator creates a user.
2. Operator issues a token for the user.
3. The token can be used by another service if that service accepts pre-issued tokens.
