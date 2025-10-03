from typing import Dict, Set
from fastapi import WebSocket
import asyncio

class WSManager:
    """
    Gerencia conexões WebSocket por sala, prevenindo duplicação de envio.
    """
    def __init__(self):
        # rooms: dict { room_name: set of WebSockets }
        self.rooms: Dict[str, Set[WebSocket]] = {}
        # locks por sala para evitar envio simultâneo que cause duplicação
        self._locks: Dict[str, asyncio.Lock] = {}

    async def connect(self, room: str, ws: WebSocket):
        """
        Aceita o WebSocket e adiciona na sala.
        Não adiciona duplicado.
        """
        await ws.accept()
        if room not in self.rooms:
            self.rooms[room] = set()
            self._locks[room] = asyncio.Lock()
        if ws not in self.rooms[room]:
            self.rooms[room].add(ws)

    def disconnect(self, room: str, ws: WebSocket):
        """
        Remove WebSocket da sala.
        """
        conns = self.rooms.get(room)
        if conns and ws in conns:
            conns.remove(ws)
            if not conns:
                # remove a sala vazia e o lock
                self.rooms.pop(room, None)
                self._locks.pop(room, None)

    async def broadcast(self, room: str, payload: dict):
        """
        Envia uma mensagem para todos os WebSockets da sala,
        usando lock para evitar envio simultâneo que gere duplicação.
        """
        if room not in self.rooms:
            return
        lock = self._locks.get(room)
        async with lock:
            to_remove = []
            for ws in list(self.rooms[room]):
                try:
                    await ws.send_json(payload)
                except Exception:
                    to_remove.append(ws)
            for ws in to_remove:
                self.disconnect(room, ws)
