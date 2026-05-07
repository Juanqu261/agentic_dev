from contextlib import asynccontextmanager

from fastapi import FastAPI

from pod_brain import get_graph
from routes import agui as agui_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_graph()
    yield


app = FastAPI(title="Agentic DevStudio API", version="0.1.0", lifespan=lifespan)

app.include_router(agui_routes.router)
