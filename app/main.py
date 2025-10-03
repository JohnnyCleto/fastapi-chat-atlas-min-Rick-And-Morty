from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import asyncio
import json
import time

from .config import APP_HOST, APP_PORT
from .database import get_db
from .models import MessageIn, serialize
from .ws_manager import WSManager
from .routes import messages as messages_router
from .routes import rooms as rooms_router
from .routes import users as users_router
from .redis_client import get_redis, publish_message, push_recent

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"

app = FastAPI(title="FastAPI Chat (Grupos + Perfis)")

# ---------------------------
# Middlewares
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Rotas e estáticos
# ---------------------------
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(messages_router.router)
app.include_router(rooms_router.router)
app.include_router(users_router.router)

manager = WSManager()

# ---------------------------
# Configs
# ---------------------------
PRESENCE_WINDOW = 60       # segundos considerados "online"
RATE_LIMIT_WINDOW = 5      # janela rate-limit em segundos
RATE_LIMIT_MAX = 8         # mensagens por janela

# ---------------------------
# Background tasks
# ---------------------------
_pubsub_task: asyncio.Task | None = None
_presence_cleaner_task: asyncio.Task | None = None

# ---------------------------
# Redis utils
# ---------------------------
async def wait_redis_ready(timeout: int = 10):
    """Aguarda Redis estar disponível antes de prosseguir"""
    r = get_redis()
    start = time.time()
    while True:
        try:
            await r.ping()
            return
        except Exception:
            if time.time() - start > timeout:
                raise TimeoutError("Redis não disponível após espera")
            await asyncio.sleep(0.5)

async def redis_pubsub_listener():
    """Recebe mensagens via pubsub e retransmite para WSManager"""
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.psubscribe("chat:*")
    try:
        async for message in pubsub.listen():
            if message.get("type") not in ("message", "pmessage"):
                continue

            channel = message.get("channel")
            if isinstance(channel, bytes):
                channel = channel.decode()

            if not channel.startswith("chat:"):
                continue

            room = channel.split(":", 1)[1]
            data = message.get("data")

            try:
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode()
                payload = json.loads(data)
            except Exception:
                continue

            await manager.broadcast(room, {"type": "message", "item": payload})

    except asyncio.CancelledError:
        await pubsub.punsubscribe()
        await pubsub.close()
        raise
    finally:
        try:
            await pubsub.punsubscribe()
            await pubsub.close()
        except Exception:
            pass

async def presence_cleaner():
    """Remove usuários antigos dos ZSETs de presença"""
    r = get_redis()
    while True:
        try:
            now = int(time.time())
            keys = await r.keys("chat:*:presence")
            for key in keys:
                await r.zremrangebyscore(key, 0, now - PRESENCE_WINDOW)
        except Exception:
            pass
        await asyncio.sleep(10)

# ---------------------------
# Startup / Shutdown
# ---------------------------
@app.on_event("startup")
async def startup_event():
    global _pubsub_task, _presence_cleaner_task
    await wait_redis_ready()
    loop = asyncio.get_event_loop()
    _pubsub_task = loop.create_task(redis_pubsub_listener())
    _presence_cleaner_task = loop.create_task(presence_cleaner())

@app.on_event("shutdown")
async def shutdown_event():
    global _pubsub_task, _presence_cleaner_task
    if _pubsub_task:
        _pubsub_task.cancel()
        try:
            await _pubsub_task
        except:
            pass
    if _presence_cleaner_task:
        _presence_cleaner_task.cancel()
        try:
            await _presence_cleaner_task
        except:
            pass
    r = get_redis()
    try:
        await r.close()
    except Exception:
        pass

# ---------------------------
# Rate-limit
# ---------------------------
async def check_rate_limit(room: str, username: str) -> bool:
    r = get_redis()
    key = f"rl:{room}:{username}"
    val = await r.incr(key)
    if val == 1:
        await r.expire(key, RATE_LIMIT_WINDOW)
    return val <= RATE_LIMIT_MAX

# ---------------------------
# WebSocket Handler
# ---------------------------
@app.websocket("/ws/{room}")
async def ws_room(ws: WebSocket, room: str):
    await manager.connect(room, ws)
    r = get_redis()
    try:
        # Histórico (Redis ou Mongo)
        recent_key = f"chat:{room}:recent"
        recent = await r.lrange(recent_key, 0, -1)
        items = []

        if recent:
            for raw in reversed(recent):
                try:
                    items.append(json.loads(raw))
                except Exception:
                    pass
        else:
            cursor = get_db()["messages"].find({"room": room}).sort("_id", -1).limit(50)
            async for d in cursor:
                items.append(serialize(d))
            items.reverse()

        await ws.send_json({"type": "history", "items": items})

        presence_key = f"chat:{room}:presence"

        while True:
            payload = await ws.receive_json()

            # Heartbeat → atualiza presença
            if isinstance(payload, dict) and payload.get("type") == "heartbeat":
                user = payload.get("username", "anon")
                await r.zadd(presence_key, {user: int(time.time())})
                continue

            # Validação da mensagem
            try:
                m = MessageIn(**payload)
            except Exception:
                continue

            if not m.content.strip():
                continue

            # Rate limit
            allowed = await check_rate_limit(room, m.username)
            if not allowed:
                await ws.send_json({
                    "type": "error",
                    "detail": f"Rate limit: max {RATE_LIMIT_MAX} msgs / {RATE_LIMIT_WINDOW}s"
                })
                continue

            # Persiste no Mongo
            doc = {
                "room": room,
                "username": m.username,
                "avatar": m.avatar,
                "content": m.content,
                "created_at": datetime.now(timezone.utc),
            }
            res = await get_db()["messages"].insert_one(doc)
            doc["_id"] = res.inserted_id
            serial = serialize(doc)

            # Cache no Redis e Pub/Sub
            await push_recent(room, serial, maxlen=50)
            await publish_message(room, serial)
            await r.zadd(presence_key, {m.username: int(time.time())})

            # Retorna ao remetente
            await ws.send_json({"type": "message", "item": serial})

    except WebSocketDisconnect:
        manager.disconnect(room, ws)
    except Exception:
        manager.disconnect(room, ws)
        raise

# ---------------------------
# Rotas simples
# ---------------------------
@app.get("/chat")
async def get_chat():
    return FileResponse("app/static/chat.html")
