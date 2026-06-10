# Silicofeller Bridge (backend skeleton)

FastAPI service that the Silicofeller editor talks to. This skeleton wires
up the HTTP contract, models, and a service layer with cache, but contains
**no Qiskit Metal logic** — every service method raises
`NotImplementedError` until the Qiskit Metal integration lands.

## Run

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000
```

Then point the frontend at it:

```bash
# .env (project root)
VITE_BRIDGE_URL=http://localhost:8000
```

`GET /health` should return `{ "status": "ok", ... }`. All component and
design endpoints currently return HTTP 501 with the
`{ "error": { "code": "NOT_IMPLEMENTED", ... } }` envelope.

## Layout

```
backend/
├── app.py                # FastAPI entrypoint, CORS, error envelope
├── config.py             # env-driven Settings
├── routes/               # HTTP layer (thin)
├── services/             # interfaces — Qiskit Metal plugs in here
├── models/               # Pydantic models mirroring the frontend types
├── cache/                # in-memory registry cache (invalidatable)
└── contracts/            # backend-facing copy of bridge + geometry docs
```

## Extension points

Implement these subclasses (or replace the module-level singletons) once
Qiskit Metal is available:

- `services/component_registry.py::ComponentRegistryService.discover_components`
- `services/metadata_service.py::MetadataService.extract_metadata`
- `services/pin_service.py::PinService.extract_pins`
- `services/render_service.py::RenderService.render_component_preview`
- `services/render_service.py::RenderService.render_design`
- `services/render_service.py::RenderService.validate_design`
- `services/codegen_service.py::CodegenService.generate`

No other file needs to change to bring the bridge online.
