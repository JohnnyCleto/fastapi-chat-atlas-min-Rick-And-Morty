# redis_client.py
import os
import redis.asyncio as redis
from typing import Any
import json

# Configurações via ENV, com defaults para Docker Compose
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

_redis: redis.Redis | None = None

def get_redis() -> redis.Redis:
    """
    Retorna o cliente Redis singleton para evitar múltiplas conexões.
    """
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
    return _redis

async def publish_message(channel: str, message: Any):
    """
    Publica uma mensagem em Pub/Sub Redis para a sala.
    """
    r = get_redis()
    if not isinstance(message, str):
        message = json.dumps(message, default=str)
    await r.publish(f"chat:{channel}", message)

async def push_recent(room: str, value: Any, maxlen: int = 50):
    """
    Armazena a última mensagem no Redis LIST de mensagens recentes da sala.
    """
    r = get_redis()
    if not isinstance(value, str):
        value = json.dumps(value, default=str)
    key = f"chat:{room}:recent"
    await r.lpush(key, value)
    await r.ltrim(key, 0, maxlen - 1)
