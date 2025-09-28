from fastapi import APIRouter, HTTPException, Query, status
from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional

from ..database import get_db
from ..models import MessageIn, MessageOut

router = APIRouter(prefix="/rooms", tags=["Messages"])

def serialize_message(doc: dict) -> dict:
    return {
        "id": str(doc.get("_id") or doc.get("id") or ""),
        "room": doc.get("room", ""),
        "username": doc.get("username", ""),
        "content": doc.get("content", ""),
        "avatar": doc.get("avatar"),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None
    }

@router.get("/{room}/messages")
async def get_messages(
    room: str,
    limit: int = Query(50, ge=1, le=200),
    before_id: Optional[str] = Query(None)
):
    """
    Retorna mensagens de uma sala. Paginação com before_id (ObjectId).
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
    Rota REST para enviar mensagem (útil para clients não-WS).
    """
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mensagem não pode ser vazia.")

    doc = {
        "room": room,
        "username": payload.username,
        "content": content,
        "avatar": payload.avatar,
        "created_at": datetime.now(timezone.utc),
    }
    res = await get_db()["messages"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize_message(doc)
