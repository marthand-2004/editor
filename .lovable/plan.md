## Goal

Evolve the uploaded Quantum_Studio frontend into the Silicofeller schematic editor inside this project. Preserve reusable editor infrastructure (canvas, panels, toolbar, types) and replace the hardcoded component system with a typed, bridge-ready API client that will later talk to the Qiskit Metal Python service via `BRIDGE_URL`. Qiskit Metal remains the single source of truth for components, parameters, pins, geometry, connectivity, and generated Python code.

## Current state

- `/dev-server` is a fresh TanStack Start template — `src/routes/index.tsx` is the blank placeholder, no editor yet.
- Uploaded `Quantum_Studio-main/frontend` is the same stack (TanStack Start v1, React 19, Tailwind v4, shadcn) and contains:
  - `src/components/quantum-editor/` — 8 files, ~4.3k LOC: `editor-canvas`, `editor-toolbar`, `bottom-panel`, `property-inspector`, `component-library`, `material-selector`, `cad-viewport`, `editor-types`.
  - Routes under `src/routes/_app/`: `quantum-editor.tsx`, `schematic-editor.tsx`, plus 18 other app shell routes.
  - Auth shell, `lib/auth/auth-context.tsx`, `lib/design-context.tsx`, `lib/project-context.tsx`, `lib/api/backend.ts`.

## Migration analysis

**Reuse unchanged** — `editor-canvas`, `editor-toolbar`, `bottom-panel`, `property-inspector` framework, `material-selector`, shadcn primitives, `cn` util, hooks.

**Refactor** — `editor-types` (strip embedded component/parameter definitions; keep placement/connection/selection/viewport types), `property-inspector` (schema from bridge), `component-library` (list from bridge), `cad-viewport` (SVG preview from bridge), `design-context` (placements + connections only).

**Replace** — any hardcoded component registry, parameter defaults, pin layouts, routing math, code generation → bridge calls.

---

## Phase 0 — Qiskit Metal Validation (NEW)

Pre-implementation gate. Goal: prove the bridge contract is achievable before front-end code depends on it. **No Python code is written in this project** (per user constraint), so this phase produces a written validation contract + a runnable checklist that the future bridge implementer must satisfy. The frontend ships with a Phase-0 status panel that pings the bridge for each capability and shows pass/fail.

Capabilities to validate (per future bridge):

1. **Component discovery** — `GET /components` returns a list of `{id, name, module, category}` for every `QComponent` subclass registered in Qiskit Metal.
2. **Metadata extraction** — `GET /components/{id}/metadata` returns parameter schema (name, type, unit, default, description), inferred from `default_options` + class docstrings.
3. **Pin extraction** — `GET /components/{id}/pins` returns pin list with `{name, direction, default_position_hint}` from `QComponent` pin metadata.
4. **Preview generation** — `GET /components/{id}/preview?params=...` returns SVG (MVP) of the component rendered at its default or supplied parameters.

Required test fixtures the bridge must pass:

- `TransmonPocket` — qubit with pads, validates pin extraction + parameter schema breadth.
- `TransmonCross` — alternate qubit geometry, validates polymorphism handling.
- `LaunchpadWirebond` — IO component, validates non-qubit categories.
- `RouteMeander` — routing component, validates connection-driven geometry.

Deliverables in this project:

- `docs/bridge-contract.md` — full endpoint contract + the 4-component validation matrix.
- `src/components/quantum-editor/bridge-status.tsx` — UI panel that calls each endpoint against the 4 fixtures and shows pass/fail/skipped. Visible during development; collapsible in production.
- Bridge-status endpoint usage: `listComponents()` → assert 4 fixture IDs present → for each ID: `getMetadata`, `getPins`, `getPreview`.

---

## Bridge client (`src/lib/bridge/`)

- `types.ts`:
  - `ComponentSummary`, `ComponentDetail`, `ComponentMetadata` (parameter schema), `PinSpec`, `ComponentPreview` (SVG string + viewBox).
  - `Placement` (component id, instance id, position, rotation, param overrides).
  - `Connection` (first-class: `{id, fromPin: {placementId, pinName}, toPin: {placementId, pinName}, routeComponentId?, routeOverrides?}`).
  - `Route` (derived: bridge-generated geometry for a connection).
  - `DesignDocument` (placements, connections, viewport, selection).
  - `ValidationResult`, `GeneratedCode`, `RenderResult`.
- `client.ts` — `fetch` client reading `import.meta.env.VITE_BRIDGE_URL`. Endpoints:
  - `GET /components`, `GET /components/{id}`, `GET /components/{id}/metadata`, `GET /components/{id}/pins`, `GET /components/{id}/preview`
  - `POST /design/validate`, `POST /design/generate-code`, `POST /design/render`
  - Each returns `{ data, error }`; never throws. "Bridge not configured" empty state when `VITE_BRIDGE_URL` is unset.
- `queries.ts` — TanStack Query `queryOptions` for each GET. Uses Query's cache as the **registry cache layer** (see below).
- `adapters.ts` — DTO → view-model mappers so editor never imports bridge types directly.

### Registry Caching (NEW)

- Component registry (`/components`) and per-component metadata/pins/preview are cached client-side via TanStack Query with:
  - `staleTime: 24h` for registry list and metadata (Qiskit Metal registry is effectively static per bridge process).
  - `staleTime: 24h` for preview at default params; `staleTime: 0` for preview with user-supplied params.
  - `gcTime: 7d`.
- Manual invalidation: a "Refresh registry" action in the bridge-status panel calls `queryClient.invalidateQueries({queryKey: ["bridge","components"]})`.
- The bridge contract document specifies that the Python side SHOULD additionally cache its own introspection results (process-lifetime memo) so cold requests don't rescan Qiskit Metal — documented as a bridge requirement, not implemented here.
- `lastSeen` timestamp persisted to `localStorage` so the UI can show "Registry cached 3h ago".

---

## Connection Architecture (NEW)

Connections are first-class objects in `DesignDocument`. Routes are derived, not stored.

```text
Pin (bridge-defined)  →  Connection (frontend-owned)  →  Route (bridge-generated)
   on a placement         {from,to,routeComponentId}      geometry returned by bridge
```

Workflow:

1. User clicks a pin on placement A → editor enters "connecting" mode, highlights compatible pins on other placements (compatibility rule supplied by bridge metadata; frontend just renders the flag).
2. User clicks a pin on placement B → a `Connection` object is added to `DesignDocument.connections` with a default `routeComponentId` (e.g. `RouteMeander`) chosen from a bridge-provided list of valid route components.
3. Frontend sends the design (placements + connections) to `POST /design/render`. Bridge instantiates route components for each connection and returns the rendered geometry + a `routeId` per connection.
4. Editor renders the returned route SVG; user can select a connection and edit `routeOverrides` (jog distance, total length, etc.) via the property inspector using metadata from `GET /components/{routeComponentId}/metadata`.

Frontend never computes routing geometry. Deleting a placement cascades to remove connections referencing it. Connection IDs are stable so undo/redo works.

---

## Geometry Strategy (NEW)

Documented in `docs/geometry-strategy.md` and reflected in the bridge contract.

**MVP — SVG-based rendering**

- Bridge returns SVG strings for component previews and full design renders.
- `GET /components/{id}/preview` → `{svg: string, viewBox: {x,y,w,h}, units: "um"|"mm"}`.
- `POST /design/render` → `{svg: string, viewBox, layers: [{name, svg}], routes: [{connectionId, svg}]}`.
- Frontend renders SVG inline, applies pan/zoom via the existing `editor-canvas` viewport transform, and overlays interactive pin/connection handles in a separate SVG layer.
- Pros: zero geometry math in the frontend, trivial to render, scalable, prints cleanly.

**Future — QGeometry → JSON rendering**

- Bridge exposes `POST /design/render?format=qgeometry` returning Qiskit Metal's `QGeometry` tables serialized as JSON (per-layer polygons, paths, junctions with explicit coordinates).
- Frontend renders via a pluggable renderer (Canvas2D or WebGL) for large designs (>10k geometries) where SVG performance degrades.
- Renderer interface (`src/lib/bridge/renderer.ts`) is introduced now as a single-implementation abstraction (`SvgRenderer`) so the swap is non-breaking. No QGeometry code ships in MVP.

---

## Editor components (`src/components/quantum-editor/`)

Port the 8 files from the zip with these edits:

- `editor-types.ts` — remove embedded component/parameter definitions; keep placement/connection/viewport/selection/tool types only. Re-export bridge types where needed.
- `component-library.tsx` — replace static list with `useSuspenseQuery(componentsQueryOptions)`.
- `property-inspector.tsx` — accept `metadata: ComponentMetadata` prop; render fields generically. Also handles connection property editing when a connection is selected.
- `cad-viewport.tsx` — render SVG returned by bridge; no local geometry math. Empty state when bridge unconfigured.
- `editor-canvas.tsx` — port; add pin-click → connection-creation interaction.
- `editor-toolbar.tsx` — port; add "Validate", "Generate Code", "Render" buttons wired to bridge endpoints.
- `bottom-panel.tsx` — port and add the **Generated Code tab** (see below).
- `material-selector.tsx` — port as-is.
- All imports normalized to `@/` alias.

### Generated Code Panel (NEW, in bottom-panel)

Reserved tab from day one. Tabs: `Console | Validation | Generated Code | Bridge Status`.

- Calls `POST /design/generate-code` with the current `DesignDocument`.
- Displays returned Python in a read-only code view with syntax highlighting (lightweight, no Monaco — use `prismjs` or a minimal `<pre>` highlighter).
- Buttons: **Copy**, **Download `design.py`**, **Regenerate**.
- Auto-regenerates (debounced 1s) when design changes if user enables "Live sync".
- Empty state when bridge unconfigured: shows the contract for `POST /design/generate-code` so the user understands what it will produce.

---

## Editor state (`src/lib/editor/`)

- `design-store.tsx` — React context holding `DesignDocument` (placements, **connections as first-class**, selection, viewport, undo/redo). Pure frontend state.
- `use-undo-redo.ts` — extracted history hook (placement add/move/delete, param edit, connection add/delete/edit).
- Selection model supports placements **and** connections.

---

## Route

- `src/routes/schematic-editor.tsx` — top-level route. Wraps the editor in `DesignStoreProvider`, sets `errorComponent` + `notFoundComponent`, per-route `head()`. Uses `useSuspenseQuery(componentsQueryOptions())` inside a `<Suspense>` boundary; loader calls `context.queryClient.ensureQueryData(componentsQueryOptions())` so first render is non-blocking on cache hit.
- `src/routes/index.tsx` — replace placeholder with a minimal landing linking to `/schematic-editor`.

## Dependencies

`bun add`: `react-resizable-panels`, `motion`, `prismjs` (+ `@types/prismjs`) for the code panel. Verify Radix primitives at port time.

## Env

- `.env.example` with `VITE_BRIDGE_URL=http://localhost:8000` and a comment that bridge runs separately.

## Out of scope

- Python bridge implementation (only the **contract document** is produced here).
- Mock component data — explicitly forbidden by user. Empty states everywhere instead.
- Auth, projects, dashboard, billing, and 18 other `_app/*` routes from the zip.
- 3D/CAD geometry computation in the frontend.
- QGeometry-JSON renderer implementation (interface only).

## Technical notes

- TanStack Start conventions: loader `ensureQueryData`, component `useSuspenseQuery`. No `useEffect`+`fetch`.
- Public route — bridge calls happen from components, not loaders, to avoid SSR prerender failures and because CORS is the bridge's responsibility.
- All editor code stays presentational; quantum truth lives behind the bridge boundary.

## Execution order after approval

1. `docs/bridge-contract.md` + `docs/geometry-strategy.md`
2. Deps install
3. Bridge `types.ts` → `client.ts` → `queries.ts` → `renderer.ts` (SVG impl) → `adapters.ts`
4. Editor port (8 components + types refactor)
5. `design-store` + undo/redo with first-class connections
6. Bottom-panel Generated Code tab + Bridge Status panel
7. Route + index update + `.env.example`
8. Verify build
