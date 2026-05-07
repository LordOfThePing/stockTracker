import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import overview, positions, connectors, history, refresh, manual, instruments, admin
from .scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router)
app.include_router(positions.router)
app.include_router(connectors.router)
app.include_router(history.router)
app.include_router(refresh.router)
app.include_router(manual.router)
app.include_router(instruments.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
