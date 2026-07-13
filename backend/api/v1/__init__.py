"""API v1 routes."""

from fastapi import APIRouter
from .companies import router as companies_router
from .metrics import router as metrics_router
from .graph import router as graph_router
from .fragility import router as fragility_router
from .risks import router as risks_router
from .narrative import router as narrative_router
from .monitoring import router as monitoring_router

router = APIRouter(prefix="/api/v1")
router.include_router(companies_router)
router.include_router(metrics_router)
router.include_router(graph_router)
router.include_router(fragility_router)
router.include_router(risks_router)
router.include_router(narrative_router)
router.include_router(monitoring_router)

# ponytail: route imports added per epic (E3: metrics, E4: graph, E5a: fragility, E5b: risks+narrative)
