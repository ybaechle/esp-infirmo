import asyncio
import json
import os
import time
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuthSession, User
from app.realtime import channel
from app.services.sessions import digest

router = APIRouter(tags=["realtime"])

AUTH_TIMEOUT = 5
POLL = 1.0
UNAUTHORIZED = 4401


def authenticate(db: Session, token: str) -> tuple[User, int] | None:
    session = db.scalar(
        select(AuthSession).where(AuthSession.access_hash == digest(token))
    )
    if session is None or session.revoked_at is not None:
        return None
    if session.access_expires_at <= int(time.time()):
        return None
    user = db.get(User, session.user_id)
    return (
        (user, session.access_expires_at) if user and user.status == "active" else None
    )


async def read_token(websocket: WebSocket) -> str | None:
    """Le jeton arrive dans le premier message, jamais dans l'URL (qui finit dans les journaux)."""
    try:
        first = json.loads(
            await asyncio.wait_for(websocket.receive_text(), AUTH_TIMEOUT)
        )
    except (TimeoutError, ValueError, WebSocketDisconnect):
        return None
    token = first.get("type") == "auth" and first.get("token")
    return token if isinstance(token, str) and len(token) <= 128 else None


async def watch_client(websocket: WebSocket):
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


@router.websocket("/ws")
async def events(websocket: WebSocket, db: Annotated[Session, Depends(get_db)]):
    await websocket.accept()
    token = await read_token(websocket)
    found = authenticate(db, token) if token else None
    db.close()
    if found is None:
        await websocket.close(UNAUTHORIZED)
        return
    user, expires_at = found
    await websocket.send_json({"type": "ready"})
    client = aioredis.from_url(os.environ["REDIS_URL"])
    pubsub = client.pubsub()
    await pubsub.subscribe(channel(user.id))
    closed = asyncio.create_task(watch_client(websocket))
    try:
        while not closed.done():
            if int(time.time()) >= expires_at:
                await websocket.close(UNAUTHORIZED)
                return
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=POLL
            )
            if message:
                await websocket.send_text(message["data"].decode())
    except WebSocketDisconnect:
        pass
    finally:
        closed.cancel()
        await pubsub.aclose()
        await client.aclose()
