# Geometry Strategy

The editor renders chip layouts that ultimately come from Qiskit Metal's
`QGeometry` tables. We have two viable transport formats; we pick the simpler
one now and keep the door open for the more powerful one later.

## MVP — SVG strings from the bridge

**Status:** active.

The bridge serializes each component preview and full-design render to an
SVG fragment (the inner markup without a `<svg>` wrapper) plus a `viewBox`
and a unit string. The frontend embeds the fragment inside its own canvas
SVG and applies pan/zoom via a single CSS-style transform on the parent
group.

**Why SVG first:**
- Zero geometry math in the frontend — Qiskit Metal stays the single source
  of truth for shapes.
- Trivial to render in React: `<g dangerouslySetInnerHTML={{ __html: svg }} />`.
- Scales losslessly; supports printing/export.
- Naturally diffable per route — `POST /design/render` returns per-connection
  route SVGs so the editor can swap one route without re-rendering the
  whole design.

**Endpoints used:**
- `GET /components/{id}/preview` → component thumbnail in the library and
  inline preview at placement time.
- `POST /design/render` → full layout with `layers[]` and `routes[]`.

**Performance envelope:** SVG is the right pick up to roughly the
single-digit-thousands-of-polygons range. Beyond that the DOM tree becomes
the bottleneck, not the network. The 4-fixture Phase-0 designs are deeply
inside this envelope.

## Future — QGeometry → JSON

**Status:** planned, not implemented. Interface stub in
`src/lib/bridge/renderer.ts`.

When designs grow past the SVG performance envelope the bridge will be
extended with `POST /design/render?format=qgeometry`, returning the
`QGeometry` tables Qiskit Metal already maintains, serialized as JSON:

```json
{
  "layers": [
    { "name": "metal",     "polygons": [ { "points": [[x,y], ...], "holes": [] } ], "paths": [ ... ] },
    { "name": "junctions", "polygons": [ ... ] }
  ],
  "units": "um"
}
```

The frontend will then render via a Canvas2D or WebGL renderer behind the
same `Renderer` interface that ships today as `SvgRenderer`. No changes to
the editor state model, the bridge contract for non-render endpoints, or the
user-facing UI.

**When to switch:** when render times for `POST /design/render` exceed
~150 ms for a typical design, or DOM node count for a single layout
crosses ~5 000.

## Renderer interface

```ts
// src/lib/bridge/renderer.ts
export interface Renderer {
  render(result: RenderResult): React.ReactNode;
  renderPreview(preview: ComponentPreview, transform: { x: number; y: number; rotation: number }): React.ReactNode;
}
```

Only `SvgRenderer` exists today. The interface is kept so the swap is
non-breaking.
