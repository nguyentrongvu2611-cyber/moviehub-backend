import asyncio
from typing import Dict, Set
class SSEManager:
    def __init__(self):
        self.connections: Dict[int, Set[asyncio.Queue]] = {}
    async def connect(self, user_id: int) -> asyncio.Queue:
        queue = asyncio.Queue()
        if user_id not in self.connections:
            self.connections[user_id] = set()
        self.connections[user_id].add(queue)
        return queue
    def disconnect(self, user_id: int, queue: asyncio.Queue):
        if user_id in self.connections:
            self.connections[user_id].remove(queue)
            if not self.connections[user_id]:
                del self.connections[user_id]
    async def send_event(self, user_id: int, event_type: str, data: dict):
        """Gửi sự kiện tức thì xuống cho user cụ thể"""
        if user_id in self.connections:
            message = {"type": event_type, "data": data}
            for queue in list(self.connections[user_id]):
                await queue.put(message)
sse_manager = SSEManager()


