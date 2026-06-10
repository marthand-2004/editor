"""Qiskit Metal pin extraction."""
from __future__ import annotations

import logging
import math

from ..cache import registry_cache
from ..models import ComponentPins, PinHint, PinSpec

log = logging.getLogger(__name__)

# Qiskit Metal pin coordinates are in mm; frontend expects um.
MM_TO_UM = 1000.0

_renderers_patched = False


def _patch_renderers_once() -> None:
    """Monkey-patch _start_renderers to a no-op exactly once.

    Prevents qiskit-metal from loading optional renderers that require
    gdspy or pyaedt, neither of which is installed in this environment.
    """
    global _renderers_patched
    if _renderers_patched:
        return
    try:
        from qiskit_metal.designs import design_base

        if not getattr(design_base.QDesign._start_renderers, "_is_noop", False):
            def _noop(self) -> None:  # noqa: ANN001
                pass
            _noop._is_noop = True  # type: ignore[attr-defined]
            design_base.QDesign._start_renderers = _noop
        log.info("Renderer patch applied.")
    except Exception:
        log.exception("Could not patch _start_renderers")
    _renderers_patched = True


def _seed_connection_pads(cls: type) -> dict:
    """Return a connection_pads dict that will trigger pin generation.

    Two cases:
    1. Component has named default connection_pads (e.g. TransmonPocket:
       a, b, c, d) → return those.
    2. Component has _default_connection_pads template but empty
       connection_pads (e.g. TransmonCross) → create one pad per arm
       using standard compass names and the template defaults.
    """
    from addict import Dict as AdDict

    raw_opts = None
    for klass in cls.__mro__:
        candidate = getattr(klass, "default_options", None)
        if candidate is not None:
            raw_opts = candidate
            break

    if raw_opts is None:
        return {}

    # Case 1: explicit named connection pads
    existing_pads = raw_opts.get("connection_pads") if hasattr(raw_opts, "get") else None
    if existing_pads is not None and hasattr(existing_pads, "keys") and len(existing_pads) > 0:
        if hasattr(existing_pads, "to_dict"):
            return AdDict(existing_pads.to_dict())
        return AdDict(dict(existing_pads))

    # Case 2: component has _default_connection_pads template → seed arms
    template = raw_opts.get("_default_connection_pads") if hasattr(raw_opts, "get") else None
    if template is None:
        return {}

    base = {}
    if hasattr(template, "to_dict"):
        base = template.to_dict()
    elif isinstance(template, dict):
        base = dict(template)

    # Standard cross-arm locations: 0=west, 90=north, 180=east, 270=south
    arms = {
        "west":  {"connector_location": "0"},
        "north": {"connector_location": "90"},
        "east":  {"connector_location": "180"},
        "south": {"connector_location": "270"},
    }
    pads = AdDict()
    for arm_name, overrides in arms.items():
        pad = AdDict(base)
        for k, v in overrides.items():
            pad[k] = v
        pads[arm_name] = pad

    return pads


class PinService:
    """Read pin metadata from instantiated QComponents."""

    @staticmethod
    def _cache_key(component_id: str) -> str:
        return f"pins:{component_id}"

    def extract_pins(self, component_id: str) -> ComponentPins:
        from .component_registry import component_registry_service

        summary = component_registry_service.get_component(component_id)
        if summary is None:
            raise ValueError(f"Unknown component: {component_id}")

        try:
            return self._extract_via_instantiation(component_id, summary.module)
        except Exception as exc:
            log.warning(
                "Pin extraction failed for %s: %s",
                component_id,
                exc,
                exc_info=True,
            )
            return ComponentPins(id=component_id, pins=[])

    def _extract_via_instantiation(
        self,
        component_id: str,
        module_path: str,
    ) -> ComponentPins:
        import importlib

        _patch_renderers_once()

        from qiskit_metal import designs as qm_designs

        module = importlib.import_module(module_path)
        cls = getattr(module, component_id)

        seeded_pads = _seed_connection_pads(cls)
        init_options: dict = {}
        if seeded_pads:
            init_options["connection_pads"] = seeded_pads

        design = qm_designs.DesignPlanar()
        design.overwrite_enabled = True
        component = cls(design, "_pin_probe", options=init_options)
        design.rebuild()

        pins: list[PinSpec] = []
        raw_pins = dict(component.pins)
        log.debug(
            "Component %s raw_pins keys: %s", component_id, list(raw_pins.keys())
        )

        for pin_name, pin_data in raw_pins.items():
            middle = pin_data.get("middle", [0.0, 0.0])
            normal = pin_data.get("normal", [0.0, 1.0])
            angle_deg = math.degrees(
                math.atan2(float(normal[1]), float(normal[0]))
            )
            x_um = float(middle[0]) * MM_TO_UM
            y_um = float(middle[1]) * MM_TO_UM
            pins.append(
                PinSpec(
                    name=pin_name,
                    direction="io",
                    hint=PinHint(x=x_um, y=y_um, angle=angle_deg),
                )
            )

        if not pins and seeded_pads:
            # Geometry didn't produce pins — fall back to pad names only
            for pad_name in seeded_pads.keys():
                pins.append(
                    PinSpec(
                        name=str(pad_name),
                        direction="io",
                        hint=PinHint(x=0.0, y=0.0, angle=0.0),
                    )
                )

        log.info(
            "Extracted %d pins from %s", len(pins), component_id
        )
        return ComponentPins(id=component_id, pins=pins)

    def get_pins(self, component_id: str) -> ComponentPins:
        return registry_cache.get_or_set(
            self._cache_key(component_id),
            lambda: self.extract_pins(component_id),
        )


pin_service = PinService()
