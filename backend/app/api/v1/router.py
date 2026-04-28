from fastapi import APIRouter

from app.api.v1 import exports, properties

router = APIRouter(prefix="/api/v1")
router.include_router(properties.router, prefix="/properties", tags=["properties"])
router.include_router(exports.router, prefix="/exports", tags=["exports"])
