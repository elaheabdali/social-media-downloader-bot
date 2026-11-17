"""Bot routers package."""

from handlers.media import router as media_router
from handlers.start import router as start_router

__all__ = ["media_router", "start_router"]
