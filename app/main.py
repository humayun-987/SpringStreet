from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import fund, pipeline
from app.scheduler.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Spring Street Prisma API",
    description="Backend API powering the Prisma Global Growth factsheet",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fund.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Spring Street Prisma API is running"
    }