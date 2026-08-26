from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.routers import ALL_ROUTERS

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db(); yield

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
init_db()
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
for router in ALL_ROUTERS: app.include_router(router)

@app.get("/")
def root(): return {"message":"FlexiGrid AI backend is running", "docs":"/docs", "version":settings.app_version}

@app.get("/api/health")
def health(): return {"status":"healthy", "version":settings.app_version}
