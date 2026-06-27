# auth-jwt

`auth-jwt` is a shared authentication service for small services that should use the same sign-in state.

The main idea is simple:

- A user signs in once with username and password.
- The auth service returns a long-lived `token`.
- The frontend uses this `token` to get a short-lived `temporary token`.
- Other services receive the temporary token from browser requests.
- Other services verify the temporary token by public key, or by calling `auth-jwt` when server-side verification is preferred.

This makes shared sign-in possible. Each app does not need to keep its own user table or duplicate login logic. It only needs to know how to get a temporary token and how to verify it.

## Core Concepts

`auth-jwt` has four core concepts:

- User is the identity.
- Token proves that the user has signed in.
- Permission says what the user can do.
- Service is an app that uses the auth service.

Authentication answers "who is this user". Authorization answers "can this user do this action". A service should check both when an operation is protected.

### User

User is the identity that signs in to the system.

Basic properties:

- `uid`: internal numeric user id
- `username`: human-readable login name
- `password`: stored as bcrypt hash in DB

The auth service owns the user table. Other services should not duplicate user password checking. They should trust token verification result from this service.

Users can carry permission assignments. A built-in permission applies to this auth service itself, such as creating or deleting users. A service-scoped permission applies to one external service.

### Service

Service means an external app that uses this auth service, such as a file service or a workflow service.

A service is not the same thing as a user. A service does not sign in as a person in the normal flow. A service sends users to this auth service for login, receives or verifies JWT tokens, and checks if the signed-in user has the permission needed for one action.

When a service needs its own permission, it declares a service id and integer permission code. The displayed form is:

```text
serviceId::permissionCode
```

The auth database stores `service_id` and `permission_code` as separate values. The permission assignment still belongs to a user.

### Permission

Permission is a code that says what a user can do.

Built-in auth permissions are integer codes owned by the auth service. Service-scoped permissions are integer codes under one service id. A service-scoped permission is declared by a service, then assigned to users.

One permission can include other permissions. For example, user manage permission includes user read, user create, user edit, and user delete. Permission check therefore does not only compare one code with another code. It checks whether any assigned permission directly or indirectly includes the required permission.

JWT tokens do not carry permission lists. The auth service keeps permission assignments in DB and checks them when management APIs or other services ask for authorization.

### OAuth 2.0 Compatibility

The design of this project roughly aligns with OAuth 2.0, but it uses simpler project terms.

Concept mapping:

- `token` is closest to OAuth 2.0 refresh token. It is long-lived, stored in DB, and can be revoked.
- `temporary token` is closest to OAuth 2.0 access token. It is short-lived and is issued from a valid `token`.
- `auth-jwt` works like authorization server. It signs in users and issues tokens.
- An external service works like resource server. It receives a temporary token and verifies it before serving protected resources.
- The frontend works like client. It stores the `token`, asks for a temporary token when accessing a service, and sends the temporary token to that service.

The normal rule is: use `token` to get a `temporary token`, then use `temporary token` to access services. A service should normally verify temporary tokens for user requests. It should not need to receive the stored long-lived token.

Both `token` and `temporary token` are JWT strings. A JWT has three parts:

```text
<header>.<claims>.<signature>
```

The claims include:

- `uid`: user id
- `jti`: token id, only for `token`
- `iat`: issue time
- `exp`: expiration time

The signature is created by the auth service. Other services should not edit a token. They should only send it back for verification.

Stored `token` records use integer `status_code`:

```text
1 valid
-1 expired
-2 revoked
-3 retained before permanent delete
```

The default `token` lifetime, temporary token lifetime, and retained-token delete interval are configured under `jwt` in `config/config.yaml`.

### Key Pair

The key pair is used to sign and verify JWT tokens.

- private key signs token
- public key verifies token

The private key must stay inside the auth service. The public key can be used for verification. Other services can fetch the public keys from `/.well-known/jwks.json`.

### Auth Service

The auth service is the source of truth for users, token records, and token revocation state.

It provides:

- login API to issue token
- temporary token API to issue a short-lived token from a valid stored token
- verify API to check token
- management console to operate users, DB endpoints, and token records
- permission metadata and permission check API

For more details about permission schema, built-in permission codes, and service-scoped permission declaration, see `authorization.md`.

## Shared Sign-In Process

A typical browser-based service uses `auth-jwt` through two token steps.

From user and frontend viewpoint:

1. The user opens one service that needs login.
2. The frontend sends username and password to `auth-jwt`.
3. `auth-jwt` checks the user and returns a `token`.
4. The frontend stores the `token` as sign-in state.
5. When the frontend needs to access a service, it sends the `token` to `auth-jwt` and asks for a `temporary token`.
6. The frontend sends the `temporary token` to the service it is accessing.
7. If the temporary token expires, the frontend uses the stored `token` to get a new temporary token.
8. When the user signs out, the frontend asks `auth-jwt` to revoke the stored `token` and clears local sign-in state.

From accessed service viewpoint:

1. The service receives a request with a `temporary token`.
2. The service verifies the temporary token with `auth-jwt`, or with the public key from `/.well-known/jwks.json` when local verification is enough.
3. If the action needs authorization, the service checks whether the user has the needed permission.
4. If authentication and authorization pass, the service accepts the request.

This keeps long-lived sign-in state owned by `auth-jwt` and the frontend. External services only need short-lived proof that the user is currently signed in.

## Service Integration

For a browser-based app, use the HTTP API:

```text
POST /api/token
POST /api/temporary-token
POST /api/logout
GET  /.well-known/jwks.json
```

When exposed through nginx or CloudFront, the public prefix should be `/auth/`:

```text
POST /auth/api/token
POST /auth/api/temporary-token
POST /auth/api/logout
GET  /auth/.well-known/jwks.json
```

Only these public auth routes should be proxied from nginx. The management console and `/manage/api/` should stay accessible only from the local network.

For backend-to-backend usage, use either:

- HTTP API when the caller is simple and already uses REST.
- gRPC API when the caller wants typed RPC methods and lower overhead.

## Management Console

The management console is for operating the auth service itself:

- check process status
- check configured DB endpoints
- list users
- create users
- issue and inspect JWT tokens
- view current runtime config

The console uses DB users and JWT login too. Management operations then check built-in auth permissions, such as user create or user delete.

See `deploy.md` for local launch and endpoint information.
