from fastapi import APIRouter

from app.api.v1 import (
    admin,
    applications,
    auth,
    documents,
    matching,
    messages,
    missions,
    offers,
    offices,
    patients,
    profile,
    two_factor,
)

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(two_factor.router)
router.include_router(profile.router)
router.include_router(documents.router)
router.include_router(offices.router)
router.include_router(matching.router)
router.include_router(offers.router)
router.include_router(applications.router)
router.include_router(missions.router)
router.include_router(messages.router)
router.include_router(patients.router)
router.include_router(admin.router)
