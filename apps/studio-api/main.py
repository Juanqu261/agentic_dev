import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pod_brain import get_graph
from routes import agui as agui_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_graph()
    yield


app = FastAPI(title="Agentic DevStudio API", version="0.1.0", lifespan=lifespan)

_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_allowed_origins = [
    o.strip()
    for o in os.environ.get("STUDIO_API_ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agui_routes.router)
