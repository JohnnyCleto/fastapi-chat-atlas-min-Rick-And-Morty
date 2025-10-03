# app/routes/messages.py
from fastapi import APIRouter, HTTPException, Query, status
from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional

from ..database import get_db
from ..models import MessageIn
from ..redis_client import push_recent, publish_message
from ..utils.rate_limit import check_rate_limit, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX

router = APIRouter(prefix="/rooms", tags=["Messages"])

def serialize_message(doc: dict) -> dict:
    """Serializa mensagens para envio ao cliente."""
    return {
        "id": str(doc.get("_id") or doc.get("id") or ""),
        "room": doc.get("room", ""),
        "username": doc.get("username", ""),
        "content": doc.get("content", ""),
        "avatar": doc.get("avatar"),
        "created_at": (
            doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime)
            else str(doc.get("created_at"))
        )
    }

@router.get("/{room}/messages")
async def get_messages(
    room: str,
    limit: int = Query(50, ge=1, le=200),
    before_id: Optional[str] = Query(None)
):
    """
    Retorna mensagens de uma sala (paginação via before_id)
    """
    query = {"room": room}
    if before_id:
        try:
            query["_id"] = {"$lt": ObjectId(before_id)}
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="before_id inválido.")

    cursor = get_db()["messages"].find(query).sort("_id", -1).limit(limit)
    docs = [serialize_message(d) async for d in cursor]
    docs.reverse()
    next_cursor = docs[0]["id"] if docs else None
    return {"items": docs, "next_cursor": next_cursor}

@router.post("/{room}/messages", status_code=201)
async def post_message(room: str, payload: MessageIn):
    """
    Recebe mensagem do cliente, salva no MongoDB e publica via Redis.
    Evita duplicação usando ID único e push/publish sequenciais.
    """
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mensagem não pode ser vazia.")

    # Rate limit por usuário
    allowed = await check_rate_limit(room, payload.username)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: max {RATE_LIMIT_MAX} msgs / {RATE_LIMIT_WINDOW}s"
        )

    # Cria documento da mensagem
    doc = {
        "room": room,
        "username": payload.username,
        "content": content,
        "avatar": payload.avatar,
        "created_at": datetime.now(timezone.utc),
    }

    # Inserção no MongoDB (garante ID único)
    res = await get_db()["messages"].insert_one(doc)
    doc["_id"] = res.inserted_id

    # Serializa mensagem
    serial_item = serialize_message(doc)
    message_payload = {
        "type": "message",
        "item": serial_item
    }

    # Push para Redis (lista recente) e publicação única no Pub/Sub
    await push_recent(room, serial_item, maxlen=50)
    await publish_message(room, message_payload)

    # Retorna mensagem para o remetente
    return serial_item
# -------------------------------