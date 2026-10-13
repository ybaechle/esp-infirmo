from fastapi import APIRouter

from app.api.v1 import admin, auth, two_factor

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(two_factor.router)
router.include_router(admin.router)
