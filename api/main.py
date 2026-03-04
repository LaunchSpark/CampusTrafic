from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.runs import router as runs_router
from api.routes.train import router as train_router
from api.routes.world import router as world_router

app = FastAPI(title="CampusTrafic API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(runs_router)
app.include_router(world_router)
app.include_router(train_router)
