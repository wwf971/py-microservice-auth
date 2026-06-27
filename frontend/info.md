# Management UI

React-based management interface for auth-jwt service.

## Development

```bash
cd frontend
pnpm install
pnpm dev
```

## Build for Production

```bash
pnpm build
```

This creates a `build/` directory with production-ready static files.

## Integration

The built files are served by `process_aux.py` at `/manage/` endpoint.

Login credentials are configured via:
- `MANAGE_USERNAME` 
- `MANAGE_PASSWORD`

Set these in `config_dev.py` or environment variables.
