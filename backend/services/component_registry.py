"""Qiskit Metal component discovery."""
from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
import re
from typing import List, Optional

from ..cache import registry_cache
from ..models import ComponentSummary

log = logging.getLogger(__name__)


class ComponentRegistryService:
    """Discover QComponent subclasses from the installed Qiskit Metal."""

    CACHE_KEY = "registry:components"

    def discover_components(self) -> List[ComponentSummary]:
        """Return one summary for each concrete qlibrary component class."""
        import qiskit_metal.qlibrary as qlibrary
        from qiskit_metal.qlibrary.core import QComponent

        results: List[ComponentSummary] = []
        seen: set[str] = set()

        for _, modname, _ in pkgutil.walk_packages(
            path=qlibrary.__path__,
            prefix=qlibrary.__name__ + ".",
            onerror=lambda _: None,
        ):
            try:
                module = importlib.import_module(modname)
            except Exception:
                continue

            for _, cls in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(cls, QComponent)
                    and cls is not QComponent
                    and cls.__module__ == modname
                    and cls.__name__ not in seen
                ):
                    seen.add(cls.__name__)
                    try:
                        results.append(
                            ComponentSummary(
                                id=cls.__name__,
                                name=_humanize(cls.__name__),
                                module=cls.__module__,
                                category=_infer_category(modname),
                                description=_tooltip(cls),
                            )
                        )
                    except Exception as exc:
                        log.warning("Skipping %s: %s", cls.__name__, exc)

        return results

    def list_components(self) -> List[ComponentSummary]:
        return registry_cache.get_or_set(self.CACHE_KEY, self.discover_components)

    def get_component(self, component_id: str) -> Optional[ComponentSummary]:
        for component in self.list_components():
            if component.id == component_id:
                return component
        return None

    def invalidate(self) -> None:
        registry_cache.invalidate(self.CACHE_KEY)


component_registry_service = ComponentRegistryService()


def _humanize(name: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)


def _infer_category(modname: str) -> str:
    parts = modname.split(".")
    if len(parts) < 4:
        return "other"

    segment = parts[3].lower()
    mapping = {
        "qubits": "qubits",
        "resonators": "resonators",
        "couplers": "couplers",
        "tlines": "routes",
        "terminations": "terminations",
        "launchpad": "launchpads",
        "ground": "ground",
    }
    for key, category in mapping.items():
        if key in segment:
            return category
    return "other"


def _tooltip(cls: type) -> str:
    tooltip = getattr(cls, "TOOLTIP", None)
    if tooltip:
        return str(tooltip).strip()
    doc = inspect.getdoc(cls)
    if doc:
        return doc.split("\n")[0].strip()[:200]
    return ""
