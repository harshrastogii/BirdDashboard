"""Version 1 of the platform API.

Additive-only evolution within v1; breaking changes require a v2 router mounted
alongside (see the versioning strategy).
"""

from fastapi import APIRouter

from api.routers.v1 import (
    meta, recordings, species, sites, biodiversity, models, jobs, map, environmental,
)

router = APIRouter(prefix="/api/v1")
router.include_router(meta.router)
router.include_router(recordings.router)
router.include_router(species.router)
router.include_router(sites.router)
router.include_router(biodiversity.router)
router.include_router(models.router)
router.include_router(jobs.router)
router.include_router(map.router)
router.include_router(environmental.router)
