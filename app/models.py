from pydantic import BaseModel, Field, validator
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId

# Pydantic helpers
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        return ObjectId(str(v))


# Message models
class MessageIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1, max_length=1000)
    avatar: Optional[str] = None  # URL of character avatar

    @validator("username", pre=True, always=True)
    def clean_username(cls, v):
        return (v or "anon").strip()[:50]

    @validator("content", pre=True, always=True)
    def clean_content(cls, v):
        return (v or "").strip()[:1000]

class MessageOut(BaseModel):
    id: str
    room: str
    username: str
    content: str
    avatar: Optional[str] = None
    created_at: str

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
    
# Room models
class RoomIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    is_private: bool = False
    password: Optional[str] = None

    @validator("name", pre=True, always=True)
    def clean_name(cls, v):
        return (v or "").strip()[:100]

# User profile model (saved profile)
class UserProfile(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    avatar: Optional[str] = None
