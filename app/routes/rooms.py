# app/routes/rooms.py
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict
from datetime import datetime
import time

from ..database import get_db
from ..models import RoomIn, RoomCreate
from ..redis_client import get_redis

router = APIRouter(prefix="/rooms", tags=["Rooms"])

# Constante para presença online (segundos)
PRESENCE_WINDOW = 60

# -------------------------------
# Redis Presence
# -------------------------------

@router.get("/{room}/presence")
async def get_presence(room: str):
    """
    Lista usuários online nos últimos PRESENCE_WINDOW segundos
    """
    r = get_redis()
    now = int(time.time())
    minscore = now - PRESENCE_WINDOW
    key = f"chat:{room}:presence"
    members = await r.zrangebyscore(key, minscore, now)
    return {"online": members}

# -------------------------------
# Salas
# -------------------------------

@router.get("/")
async def list_rooms():
    """
    Lista salas públicas/privadas (sem expor senhas)
    """
    db = get_db()
    cursor = db["rooms"].find({}, {"password": 0})
    rooms = [r async for r in cursor]

    for r in rooms:
        r["id"] = str(r["_id"])
        r.pop("_id", None)
    return {"rooms": rooms}

@router.post("/", status_code=201)
async def create_room(payload: RoomIn):
    """
    Cria sala pública ou privada
    """
    db = get_db()
    name = payload.name

    if await db["rooms"].find_one({"name": name}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sala já existe.")

    doc = {
        "name": name,
        "is_private": bool(payload.is_private),
        "password": payload.password if payload.is_private else None,
        "created_at": datetime.utcnow(),
    }

    res = await db["rooms"].insert_one(doc)
    return {"id": str(res.inserted_id), "name": name, "is_private": doc["is_private"]}

@router.post("/{room}/join")
async def join_room(room: str, data: Dict):
    """
    Entra em sala privada ou pública
    """
    db = get_db()
    r = await db["rooms"].find_one({"name": room})
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")

    if r.get("is_private"):
        password = data.get("password")
        if password != r.get("password"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha inválida.")

    return {"ok": True, "room": room}

@router.post("/create", status_code=201)
async def create_room_v2(payload: RoomCreate):
    """
    Endpoint alternativo para criar sala
    """
    return await create_room(payload)
