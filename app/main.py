import os
import static_ffmpeg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import Base, engine
from app.api.v1.api import api_router 

# Tự động tải và bổ sung PATH cho FFmpeg binary trên môi trường Render / Linux / Windows
static_ffmpeg.add_paths()

app = FastAPI(
    title="MovieHub API",
    version="1.0.0",
    redirect_slashes=True
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")

# Khởi tạo sẵn cấu trúc thư mục lưu trữ media
os.makedirs(os.path.join(UPLOAD_DIR, "posters"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "videos"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "avatars"), exist_ok=True)

Base.metadata.create_all(bind=engine)

# Cấu hình CORS cho phép Frontend truy cập tài nguyên HLS/API
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
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)

# Serves file tĩnh (.m3u8, .ts, poster, avatar)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/api/v1/uploads", StaticFiles(directory=UPLOAD_DIR), name="api_uploads")

# Tích hợp danh sách Router API v1
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "online", "message": "MovieHub API đang chạy thành công"}