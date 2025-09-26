from fastapi import APIRouter, Query, HTTPException
from bson import ObjectId
from datetime import datetime, timezone

from ..database import get_db
from ..models import MessageIn, serialize

router = APIRouter(prefix="/rooms", tags=["Messages"])

@router.get("/{room}/messages")
async def get_messages(
    room: str,
    limit: int = Query(20, ge=1, le=100),
    before_id: str | None = Query(None)
):
    query = {"room": room}
    if before_id:
        try:
            query["_id"] = {"$lt": ObjectId(before_id)}
        except Exception:
            raise HTTPException(status_code=400, detail="before_id inválido.")

    cursor = get_db()["messages"].find(query).sort("_id", -1).limit(limit)
    docs = [serialize(d) async for d in cursor]
    docs.reverse()
    next_cursor = docs[0]["id"] if docs else None
    return {"items": docs, "next_cursor": next_cursor}

@router.post("/{room}/messages", status_code=201)
async def post_message(room: str, payload: MessageIn):
    doc = {
        "room": room,
        "username": payload.username,
        "content": payload.content.strip(),
        "created_at": datetime.now(timezone.utc),
    }

    if not doc["content"]:
        raise HTTPException(status_code=400, detail="Mensagem não pode ser vazia.")

    res = await get_db()["messages"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)
