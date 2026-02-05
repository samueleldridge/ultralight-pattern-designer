"""
API module initialization.
"""

from .query import router
from .dashboards import router as dashboards_router
from .suggestions import router as suggestions_router
from .connections import router as connections_router
from .intelligence import router as intelligence_router
from .history import router as history_router
from .user_memory import router as user_memory_router

__all__ = [
    "router",
    "dashboards_router",
    "suggestions_router", 
    "connections_router",
    "intelligence_router",
    "history_router",
    "user_memory_router",
]
