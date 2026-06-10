# Geometry Contract (backend mirror)

The frontend MVP renders SVG fragments returned by the bridge. The full
strategy doc lives at `docs/geometry-strategy.md`; this file captures the
backend-facing obligations.

## SVG transport (MVP, active)

`GET /components/{id}/preview` and `POST /design/render` both return SVG
**fragments** (no `<svg>` wrapper) plus a `viewBox` and a unit string.

Required fields:

- `svg` — string. SVG fragment, valid as the inner content of an `<svg>`
  element on the frontend.
- `viewBox` — `{ x, y, w, h }` in the declared units.
- `units` — `"um"` or `"mm"`. Use the unit native to Qiskit Metal's output
  (`"um"` for components, `"mm"` for full designs is acceptable).
- `layers[]` (render only) — per-layer SVG fragments for layer toggling.
- `routes[]` (render only) — one SVG fragment per `Connection.id` so the
  frontend can swap a single route without re-rendering the whole design.

## QGeometry → JSON (future, not implemented)

Reserved query param: `POST /design/render?format=qgeometry`. The response
shape will be:

```json
{
  "layers": [
    { "name": "metal", "polygons": [{ "points": [[x, y]], "holes": [] }], "paths": [] }
  ],
  "units": "um"
}
```

Implement only when SVG render time exceeds ~150 ms for a typical design or
the DOM node count for a single layout crosses ~5 000.
