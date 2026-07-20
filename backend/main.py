from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

from routers import players, rankings, tournaments, matches, compare, point_by_point, live as live_router
from scheduler import start_scheduler, stop_scheduler
from live import broadcaster, live_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.broadcaster = broadcaster
    app.state.live_manager = live_manager
    start_scheduler()
    yield
    await live_manager.stop_all()
    stop_scheduler()

app = FastAPI(title="Courtside API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(players.router, prefix="/api")
app.include_router(rankings.router, prefix="/api")
app.include_router(tournaments.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(compare.router, prefix="/api")
app.include_router(point_by_point.router, prefix="/api")
app.include_router(live_router.router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}
