from fastapi import APIRouter

from app.api.v1 import (
    account,
    admin,
    applications,
    auth,
    documents,
    matching,
    messages,
    missions,
    offers,
    notifications,
    offices,
    patients,
    profile,
    two_factor,
    ws,
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
router.include_router(notifications.router)
router.include_router(ws.router)
router.include_router(account.router)
router.include_router(admin.router)
