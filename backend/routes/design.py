"""Design-level routes: validate, render, generate-code."""
from __future__ import annotations

from fastapi import APIRouter

from ..models import (
    DesignDocument,
    GeneratedCode,
    RenderResult,
    ValidationResult,
)
from ..services import codegen_service, render_service

router = APIRouter(prefix="/design", tags=["design"])


@router.post("/validate", response_model=ValidationResult)
def validate_design(design: DesignDocument) -> ValidationResult:
    return render_service.validate_design(design)


@router.post("/render", response_model=RenderResult)
def render_design(design: DesignDocument) -> RenderResult:
    return render_service.render_design(design)


@router.post("/generate-code", response_model=GeneratedCode)
def generate_code(design: DesignDocument) -> GeneratedCode:
    return codegen_service.generate(design)
