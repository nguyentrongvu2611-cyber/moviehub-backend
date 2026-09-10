import os
import static_ffmpeg
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Tự động tải và cấp đường dẫn ffmpeg binary cho môi trường (Render Linux & Windows)
static_ffmpeg.add_paths()

app = FastAPI(
    title="MovieHub API",
    version="1.0.0"
)

# Tạo sẵn các thư mục upload nếu chưa tồn tại
os.makedirs("uploads/posters", exist_ok=True)
os.makedirs("uploads/videos", exist_ok=True)
os.makedirs("uploads/avatars", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    return {
        "message": "MovieHub Backend đang hoạt động"
    }