"""Frontend-owned design document models."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

# Accept any scalar the frontend might send (bool must come before int
# because bool is a subclass of int in Python)
ParamValue = Union[bool, str, float, int]


class Placement(BaseModel):
    id: str
    componentId: str
    name: str
    x: float
    y: float
    rotation: float = 0.0
    params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("params", mode="before")
    @classmethod
    def coerce_params(cls, v: Any) -> Dict[str, Any]:
        """Flatten any nested dict values to strings so Qiskit Metal accepts them."""
        if not isinstance(v, dict):
            return {}
        result: Dict[str, Any] = {}
        for key, val in v.items():
            if isinstance(val, dict):
                # e.g. fl_options dict → JSON string
                import json
                result[key] = json.dumps(val)
            elif isinstance(val, bool):
                result[key] = val  # keep booleans as-is
            else:
                result[key] = val
        return result


class PinRef(BaseModel):
    placementId: str
    pinName: str


class Connection(BaseModel):
    id: str
    from_: PinRef = Field(alias="from")
    to: PinRef
    routeComponentId: Optional[str] = None
    routeOverrides: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class DesignDocument(BaseModel):
    placements: List[Placement] = Field(default_factory=list)
    connections: List[Connection] = Field(default_factory=list)
