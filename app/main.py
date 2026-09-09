import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import Base, engine
from app.api.v1.api import api_router 

app = FastAPI(
    title="MovieHub API",
    version="1.0.0",
    redirect_slashes=False 
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")

os.makedirs(os.path.join(UPLOAD_DIR, "posters"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "videos"), exist_ok=True)

Base.metadata.create_all(bind=engine)

# Cấu hình danh sách domain cho phép
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://nguyentrongvu2611-cyber.github.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://nguyentrongvu2611-cyber\.github\.io.*",
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/api/v1/uploads", StaticFiles(directory=UPLOAD_DIR), name="api_uploads")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "online", "message": "MovieHub API đang chạy thành công"}