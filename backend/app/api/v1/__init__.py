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

from app.errors import ErrorBody

ERRORS = {
    code: {"model": ErrorBody, "description": text}
    for code, text in {
        401: "Jeton absent, invalide ou expiré",
        403: "Rôle ou statut de compte insuffisant",
        404: "Ressource inconnue ou non accessible",
        409: "Conflit avec l'état actuel de la ressource",
        413: "Fichier trop volumineux",
        422: "Requête invalide",
        429: "Trop de tentatives",
        503: "Dépendance indisponible (base, Redis, chiffrement, IA, fournisseur 2FA)",
    }.items()
}

router = APIRouter(prefix="/api/v1", responses=ERRORS)
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
