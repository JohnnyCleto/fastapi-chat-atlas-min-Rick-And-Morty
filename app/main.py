from __future__ import annotations
import os
from typing import Optional, Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone
from pathlib import Path

# Carrega variáveis de ambiente do arquivo .env localizado na raiz do projeto
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT / ".env")

# Configurações de conexão com o MongoDB
MONGO_URL = os.getenv("MONGO_URL", "")
MONGO_DB = os.getenv("MONGO_DB", "chatdb")

# Instância principal da aplicação FastAPI
app = FastAPI(title="FastAPI Chat + MongoDB Atlas (fix datetime)")

# Middleware CORS para permitir requisições de qualquer origem (útil para desenvolvimento)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta a pasta de arquivos estáticos para servir o front-end (index.html, CSS, JS)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# --- Conexão com o Banco de Dados ---
_client: Optional[AsyncIOMotorClient] = None

def db():
    """
    Retorna a conexão com o banco de dados MongoDB.
    Se a conexão ainda não foi criada, inicializa o cliente.
    """
    global _client
    if _client is None:
        if not MONGO_URL:
            raise RuntimeError("Defina MONGO_URL no .env (string de conexão com o MongoDB Atlas).")
        _client = AsyncIOMotorClient(MONGO_URL)
    return _client[MONGO_DB]

def iso(dt: datetime) -> str:
    """
    Converte um objeto datetime em uma string ISO 8601 com timezone UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def serialize(doc: dict) -> dict:
    """
    Serializa um documento do MongoDB para um formato seguro para JSON.
    Converte ObjectId para string e datetime para ISO 8601.
    """
    d = dict(doc)
    if "_id" in d:
        d["_id"] = str(d["_id"])
    if "created_at" in d and isinstance(d["created_at"], datetime):
        d["created_at"] = iso(d["created_at"])
    return d

# --- Gerenciador de WebSockets ---
class WSManager:
    """
    Gerencia as conexões WebSocket em múltiplas salas.
    Permite broadcast de mensagens em tempo real.
    """
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, room: str, ws: WebSocket):
        """
        Aceita a conexão WebSocket e adiciona o cliente na sala especificada.
        """
        await ws.accept()
        self.rooms.setdefault(room, set()).add(ws)

    def disconnect(self, room: str, ws: WebSocket):
        """
        Remove a conexão da sala ao desconectar.
        Se a sala ficar vazia, remove a chave do dicionário.
        """
        conns = self.rooms.get(room)
        if conns and ws in conns:
            conns.remove(ws)
            if not conns:
                self.rooms.pop(room, None)

    async def broadcast(self, room: str, payload: dict):
        """
        Envia uma mensagem em tempo real para todos os clientes conectados na sala.
        Remove conexões quebradas automaticamente.
        """
        for ws in list(self.rooms.get(room, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(room, ws)

# Instância global do gerenciador de WebSockets
manager = WSManager()

# --- Rotas HTTP ---
@app.get("/", include_in_schema=False)
async def index():
    """
    Rota principal que serve o arquivo index.html (front-end).
    """
    return FileResponse("app/static/index.html")

@app.get("/rooms/{room}/messages")
async def get_messages(
    room: str,
    limit: int = Query(20, ge=1, le=100),
    before_id: str | None = Query(None)
):
    """
    Retorna as últimas mensagens de uma sala específica.
    Suporta paginação via parâmetro before_id.
    """
    query = {"room": room}
    if before_id:
        try:
            query["_id"] = {"$lt": ObjectId(before_id)}
        except Exception:
            # Se o before_id não for válido, ignora a filtragem
            pass

    cursor = db()["messages"].find(query).sort("_id", -1).limit(limit)
    docs = [serialize(d) async for d in cursor]
    docs.reverse()  # ordena do mais antigo para o mais recente
    next_cursor = docs[0]["_id"] if docs else None
    return {"items": docs, "next_cursor": next_cursor}

@app.post("/rooms/{room}/messages", status_code=201)
async def post_message(
    room: str,
    username: str = Body(..., embed=True),
    content: str = Body(..., embed=True),
):
    """
    Cria uma nova mensagem em uma sala específica.
    Limita tamanho do usuário (50 chars) e conteúdo (1000 chars).
    """
    doc = {
        "room": room,
        "username": username[:50],
        "content": content[:1000],
        "created_at": datetime.now(timezone.utc),
    }
    res = await db()["messages"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)

# --- WebSocket ---
@app.websocket("/ws/{room}")
async def ws_room(ws: WebSocket, room: str):
    """
    Gerencia a conexão WebSocket para uma sala específica.
    Envia histórico inicial e escuta novas mensagens em tempo real.
    """
    await manager.connect(room, ws)
    try:
        # Envia o histórico inicial de mensagens
        cursor = db()["messages"].find({"room": room}).sort("_id", -1).limit(20)
        items = [serialize(d) async for d in cursor]
        items.reverse()
        await ws.send_json({"type": "history", "items": items})

        # Loop principal aguardando novas mensagens
        while True:
            payload = await ws.receive_json()
            username = str(payload.get("username", "anon"))[:50]
            content = str(payload.get("content", "")).strip()
            if not content:
                continue  # ignora mensagens vazias
            doc = {
                "room": room,
                "username": username,
                "content": content,
                "created_at": datetime.now(timezone.utc),
            }
            res = await db()["messages"].insert_one(doc)
            doc["_id"] = res.inserted_id
            await manager.broadcast(room, {"type": "message", "item": serialize(doc)})
    except WebSocketDisconnect:
        manager.disconnect(room, ws)
