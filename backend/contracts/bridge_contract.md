# Bridge HTTP Contract (backend mirror)

The authoritative copy of the bridge contract lives in
`docs/bridge-contract.md` at the project root. This file mirrors the key
points for backend developers working inside `backend/`.

## Endpoints implemented by this service

| Method | Path                                       | Service                       |
|--------|--------------------------------------------|-------------------------------|
| GET    | `/health`                                  | —                             |
| GET    | `/components`                              | `ComponentRegistryService`    |
| GET    | `/components/{id}`                         | `ComponentRegistryService`    |
| GET    | `/components/{id}/metadata`                | `MetadataService`             |
| GET    | `/components/{id}/pins`                    | `PinService`                  |
| GET    | `/components/{id}/preview?params=<json>`   | `RenderService`               |
| POST   | `/design/validate`                         | `RenderService`               |
| POST   | `/design/render`                           | `RenderService`               |
| POST   | `/design/generate-code`                    | `CodegenService`              |

## Error envelope

Every 4xx/5xx response uses:

```json
{ "error": { "code": "BRIDGE_ERROR", "message": "...", "details": {} } }
```

`NotImplementedError` from any service surfaces as HTTP 501 with
`code = "NOT_IMPLEMENTED"`.

## Caching

`backend/cache/registry_cache.py` provides a process-local cache.
`registry_cache.invalidate()` should be called whenever a future hot-reload
admin endpoint detects a change in the installed Qiskit Metal version.

## Architecture invariants (do not break)

1. Qiskit Metal is the single source of truth.
2. The backend never owns design state; the frontend sends a full
   `DesignDocument` on every render / validate / codegen call.
3. Services are stateless aside from the registry cache.
4. No hardcoded component definitions live in this codebase. Discovery,
   metadata, pins, and previews all come from the live Qiskit Metal
   installation through the service interfaces.
