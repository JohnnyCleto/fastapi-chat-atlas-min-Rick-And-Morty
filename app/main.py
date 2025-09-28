from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import APP_HOST, APP_PORT
from .database import get_db
from .models import MessageIn
from .ws_manager import WSManager
from .routes import messages as messages_router
from .routes import rooms as rooms_router
from .routes import users as users_router

from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
TEMPLATES_DIR = ROOT / "templates"

app = FastAPI(title="FastAPI Chat (Grupos + Perfis)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# monta estáticos e rotas
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(messages_router.router)
app.include_router(rooms_router.router)
app.include_router(users_router.router)

manager = WSManager()

def serialize(doc: dict) -> dict:
    d = dict(doc)
    if "_id" in d:
        d["_id"] = str(d["_id"])
    if "created_at" in d and getattr(d["created_at"], "isoformat", None):
        d["created_at"] = d["created_at"].isoformat()
    return d

@app.get("/", include_in_schema=False)
async def index():
    return FileResponse("app/static/index.html")

@app.get("/chat", include_in_schema=False)
async def chat_page():
    return FileResponse("app/static/chat.html")

@app.websocket("/ws/{room}")
async def ws_room(ws: WebSocket, room: str):
    await manager.connect(room, ws)
    try:
        # envia histórico
        cursor = get_db()["messages"].find({"room": room}).sort("_id", -1).limit(50)
        items = [serialize(d) async for d in cursor]
        items.reverse()
        await ws.send_json({"type": "history", "items": items})

        while True:
            payload = await ws.receive_json()
            # valida com MessageIn
            try:
                m = MessageIn(**{
                    "username": payload.get("username", "anon"),
                    "content": payload.get("content", ""),
                    "avatar": payload.get("avatar"),
                })
            except Exception:
                # ignora payloads inválidos
                continue

            if not m.content.strip():
                continue

            doc = {
                "room": room,
                "username": m.username,
                "avatar": m.avatar,
                "content": m.content,
                "created_at": datetime.now(timezone.utc),
            }
            res = await get_db()["messages"].insert_one(doc)
            doc["_id"] = res.inserted_id
            await manager.broadcast(room, {"type": "message", "item": serialize(doc)})
    except WebSocketDisconnect:
        manager.disconnect(room, ws)
