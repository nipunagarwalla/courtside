import asyncio


class EventBroadcaster:
    def __init__(self):
        self._queues: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, match_id: str) -> asyncio.Queue:
        q = asyncio.Queue()
        self._queues.setdefault(match_id, []).append(q)
        return q

    def unsubscribe(self, match_id: str, q: asyncio.Queue):
        queues = self._queues.get(match_id, [])
        if q in queues:
            queues.remove(q)
        if not queues:
            self._queues.pop(match_id, None)

    async def broadcast(self, match_id: str, point: dict):
        for q in self._queues.get(match_id, []):
            await q.put(point)
