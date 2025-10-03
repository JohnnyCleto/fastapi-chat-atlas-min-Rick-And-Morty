# app/models.py
from pydantic import BaseModel, Field, validator
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException

# ---------------------------
# Helpers
# ---------------------------
class PyObjectId(ObjectId):
    """Custom ObjectId para validação com Pydantic."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        try:
            return ObjectId(str(v))
        except Exception:
            raise ValueError("Invalid ObjectId")

def iso(dt: datetime) -> str:
    """Converte datetime para string ISO-8601 com timezone UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def serialize(doc: dict) -> dict:
    """Serializa documentos MongoDB em JSON-safe."""
    return {
        "id": str(doc["_id"]),
        "room": doc["room"],
        "username": doc["username"],
        "content": doc["content"],
        "avatar": doc.get("avatar"),
        "created_at": iso(doc["created_at"]),
    }

# ---------------------------
# Router e Mock DB
# ---------------------------
router = APIRouter()
rooms_db = []  # ⚠️ Mock local, substitua por MongoDB real

# ---------------------------
# Room Models
# ---------------------------
class RoomCreate(BaseModel):
    """Modelo para criar sala."""
    name: str
    is_private: bool = False
    password: Optional[str] = None

class RoomIn(RoomCreate):
    """Modelo usado internamente ao listar/consultar salas."""
    id: Optional[str] = None

class RoomJoin(BaseModel):
    """Modelo para entrar em sala privada."""
    password: Optional[str] = None

@router.post("/rooms")
async def create_room(room: RoomCreate):
    """Cria uma sala nova."""
    if any(r['name'] == room.name for r in rooms_db):
        raise HTTPException(status_code=400, detail="Sala já existe")
    rooms_db.append(room.dict())
    return {"success": True}

@router.post("/rooms/{room_name}/join")
async def join_private_room(room_name: str, data: RoomJoin):
    """Entra em sala (verifica senha se for privada)."""
    room = next((r for r in rooms_db if r['name'] == room_name), None)
    if not room:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    if room['is_private']:
        if not data.password or data.password != room['password']:
            raise HTTPException(status_code=403, detail="Senha incorreta")
    return {"success": True}

# ---------------------------
# Message Models
# ---------------------------
class MessageIn(BaseModel):
    """Mensagem recebida do cliente."""
    username: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1, max_length=1000)
    avatar: Optional[str] = None

    @validator("username", pre=True, always=True)
    def clean_username(cls, v):
        """Garante username válido e tamanho máximo."""
        return (v or "anon").strip()[:50]

    @validator("content", pre=True, always=True)
    def clean_content(cls, v):
        """Garante conteúdo válido e tamanho máximo."""
        return (v or "").strip()[:1000]

class MessageOut(BaseModel):
    """Mensagem enviada ao cliente."""
    id: str
    room: str
    username: str
    content: str
    avatar: Optional[str] = None
    created_at: str

# ---------------------------
# User Profile
# ---------------------------
class UserProfile(BaseModel):
    """Perfil do usuário."""
    name: str = Field(..., min_length=1, max_length=50)
    avatar: Optional[str] = None
