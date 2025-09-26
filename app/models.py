from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId

class MessageIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1, max_length=1000)

class MessageOut(MessageIn):
    id: str
    room: str
    created_at: datetime

def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def serialize(doc: dict) -> dict:
    """
    Converte ObjectId e datetime em strings para JSON.
    """
    return {
        "id": str(doc["_id"]),
        "room": doc["room"],
        "username": doc["username"],
        "content": doc["content"],
        "created_at": iso(doc["created_at"]),
    }
