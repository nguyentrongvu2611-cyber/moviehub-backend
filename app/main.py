import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import Base, engine
from app.api.v1.api import api_router 

app = FastAPI(
    title="MovieHub API",
    version="1.0.0",
    redirect_slashes=True
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")

os.makedirs(os.path.join(UPLOAD_DIR, "posters"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "videos"), exist_ok=True)

Base.metadata.create_all(bind=engine)

# Danh sách Origins cho phép (lưu ý: KHÔNG để dấu / ở cuối domain)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "https://nguyentrongvu2611-cyber.github.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/api/v1/uploads", StaticFiles(directory=UPLOAD_DIR), name="api_uploads")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "online", "message": "MovieHub API đang chạy thành công"}