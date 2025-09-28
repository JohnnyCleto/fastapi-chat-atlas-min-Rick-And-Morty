from fastapi import APIRouter, HTTPException, status
from typing import List
from ..database import get_db
from ..models import RoomIn
from bson import ObjectId

router = APIRouter(prefix="/rooms", tags=["Rooms"])

@router.get("/")
async def list_rooms():
    """
    Lista salas (públicas e privadas sem expor senhas).
    """
    cursor = get_db()["rooms"].find({}, {"password": 0})
    rooms = [r async for r in cursor]
    # normalize id field
    for r in rooms:
        r["id"] = str(r["_id"])
        r.pop("_id", None)
    return {"rooms": rooms}

@router.post("/", status_code=201)
async def create_room(payload: RoomIn):
    """
    Cria sala pública ou privada (se password fornecido -> privada).
    """
    name = payload.name
    if await get_db()["rooms"].find_one({"name": name}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sala já existe.")

    doc = {
        "name": name,
        "is_private": bool(payload.is_private),
        "password": payload.password if payload.is_private else None,
        "created_at": __import__("datetime").datetime.utcnow(),
    }
    res = await get_db()["rooms"].insert_one(doc)
    return {"id": str(res.inserted_id), "name": name, "is_private": doc["is_private"]}

@router.post("/{room}/join")
async def join_room(room: str, data: dict):
    """
    Tenta entrar em sala. Se privada, precisa de senha correta.
    """
    r = await get_db()["rooms"].find_one({"name": room})
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")
    if r.get("is_private"):
        password = data.get("password")
        if password != r.get("password"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha inválida.")
    return {"ok": True, "room": room}
