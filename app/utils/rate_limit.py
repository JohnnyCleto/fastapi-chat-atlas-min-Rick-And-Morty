from app.redis_client import get_redis

# Janela de tempo em segundos e limite máximo de mensagens
RATE_LIMIT_WINDOW = 60  # 1 minuto
RATE_LIMIT_MAX = 5      # máximo de 5 mensagens por usuário por sala

async def check_rate_limit(room: str, username: str) -> bool:
    """
    Retorna True se o usuário puder enviar mensagem, False se excedeu.
    Usa Redis para contar mensagens enviadas por usuário por sala.
    """
    r = get_redis()
    key = f"rl:{room}:{username}"

    # INCR é atômico, então múltiplos envios simultâneos não vão quebrar
    val = await r.incr(key)

    # Se é a primeira mensagem da janela, define TTL
    if val == 1:
        await r.expire(key, RATE_LIMIT_WINDOW)

    # Retorna True se estiver dentro do limite, False caso contrário
    return val <= RATE_LIMIT_MAX
