"""Convenience launcher for the Silicofeller bridge."""
import os
import uvicorn

from .config import settings

# Resolve the backend package directory so the reloader only watches Python
# source files, not the entire project root (which includes node_modules).
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=True,
        reload_dirs=[_BACKEND_DIR],
    )
