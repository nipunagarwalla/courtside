import asyncio


class LiveMatchManager:
    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}

    async def start(self, key: str, coro):
        # Reap finished tasks so a match can be re-polled after a crash
        for k, t in list(self._tasks.items()):
            if t.done():
                self._tasks.pop(k, None)
        if key not in self._tasks:
            self._tasks[key] = asyncio.create_task(coro)
        else:
            coro.close()  # avoid "never awaited" warning

    async def stop(self, key: str):
        if task := self._tasks.pop(key, None):
            task.cancel()

    async def stop_all(self):
        for key in list(self._tasks):
            await self.stop(key)

    def active(self) -> list[str]:
        return [k for k, t in self._tasks.items() if not t.done()]
