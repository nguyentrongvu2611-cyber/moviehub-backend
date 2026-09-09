import os
import uuid
import asyncio
import aiofiles
import json
import subprocess

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User

router = APIRouter()

# Đường dẫn ffmpeg tuyệt đối
FFMPEG_EXE = r"C:\Users\nguye\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"

UPLOAD_FOLDER = "uploads"
POSTER_FOLDER = os.path.join(UPLOAD_FOLDER, "posters")
VIDEO_FOLDER = os.path.join(UPLOAD_FOLDER, "videos")
AVATAR_FOLDER = os.path.join(UPLOAD_FOLDER, "avatars")

os.makedirs(POSTER_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(AVATAR_FOLDER, exist_ok=True)

# Async Queue quản lý tin nhắn tiến trình gửi ra Frontend qua SSE
progress_queue = asyncio.Queue()


async def send_log(message: str):
    """Hàm hỗ trợ đẩy log tiến trình vào Queue và in ra console"""
    print(f"[SSE LOG]: {message}")
    await progress_queue.put(message)
    await asyncio.sleep(0.01)  # Nhường luồng để event loop kịp xử lý


def run_ffmpeg_sync(cmd: list):
    """Hàm chạy subprocess đồng bộ an toàn tuyệt đối trên Windows ThreadPool"""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    return result.returncode, result.stderr


# --- HÀM CONVERT VIDEO AN TOÀN TRÊN WINDOWS ---
async def transcode_all_resolutions_async(raw_file_path: str, video_dir_path: str):
    """Nén video sang 480p, 720p, 1080p bằng ThreadPool subprocess"""
    resolutions = {
        480: os.path.join(video_dir_path, "480p.mp4"),
        720: os.path.join(video_dir_path, "720p.mp4"),
        1080: os.path.join(video_dir_path, "1080p.mp4"),
    }

    await send_log("🚀 [Upload Route] Bắt đầu quá trình Convert Video...")

    for height, output_path in resolutions.items():
        await send_log(f"--> [Upload Route] Đang convert {height}p...")

        cmd = [
            FFMPEG_EXE,
            "-y",
            "-i", raw_file_path,
            "-vf", f"scale=-2:{height}",
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "fast",
            output_path
        ]

        try:
            returncode, stderr_output = await asyncio.to_thread(run_ffmpeg_sync, cmd)

            if returncode == 0:
                # Bắn log hoàn tất từng độ phân giải
                await send_log(f"--> [Upload Route] Hoàn tất {height}p!")
            else:
                err_msg = stderr_output[-300:] if stderr_output else "Lỗi FFmpeg không xác định"
                await send_log(f"❌ Lỗi FFmpeg khi convert {height}p: {err_msg}")

        except FileNotFoundError:
            await send_log(f"❌ Không tìm thấy file FFmpeg tại đường dẫn: {FFMPEG_EXE}")
            break
        except Exception as e:
            error_detail = str(e) or type(e).__name__
            await send_log(f"❌ Lỗi hệ thống khi convert {height}p: {error_detail}")

    # Xóa file raw tạm thời sau khi render hoàn tất
    if os.path.exists(raw_file_path):
        try:
            os.remove(raw_file_path)
            await send_log("🎉 [Upload Route] Hoàn tất xử lý tất cả độ phân giải!")
        except Exception as e:
            await send_log(f"Lỗi khi xóa file raw: {str(e)}")


# --- ENDPOINTS ---

@router.get("/stream-progress")
async def stream_progress():
    """Endpoint Stream SSE gửi tiến trình realtime về Frontend dưới dạng JSON chuẩn"""
    async def event_generator():
        while True:
            message = await progress_queue.get()
            payload = json.dumps({"message": message})
            yield f"data: {payload}\n\n"

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/poster")
async def upload_poster(
    file: UploadFile = File(...)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File phải là hình ảnh")

    extension = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(POSTER_FOLDER, filename)

    async with aiofiles.open(file_path, "wb") as buffer:
        while content := await file.read(1024 * 1024):
            await buffer.write(content)

    return {"url": f"/uploads/posters/{filename}"}


@router.post("/video")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File phải là video")

    # Báo log khởi tạo upload ngay lập tức ra Frontend
    await send_log("🚀 [Upload Route] Bắt đầu tải video lên server...")

    file_id = str(uuid.uuid4())

    video_dir_path = os.path.join(VIDEO_FOLDER, file_id)
    os.makedirs(video_dir_path, exist_ok=True)

    raw_file_path = os.path.join(video_dir_path, "raw.mp4")

    try:
        async with aiofiles.open(raw_file_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):
                await buffer.write(content)
        
        # Báo log tải file thành công
        await send_log("✅ [Upload Route] Tải file gốc thành công. Đang tiến hành Convert HLS...")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu video tạm: {str(e)}")

    background_tasks.add_task(transcode_all_resolutions_async, raw_file_path, video_dir_path)

    default_url = f"/uploads/videos/{file_id}/1080p.mp4"

    return {
        "url": default_url,
        "video_url": default_url,
        "video_urls": {
            "480p": f"/uploads/videos/{file_id}/480p.mp4",
            "720p": f"/uploads/videos/{file_id}/720p.mp4",
            "1080p": default_url
        }
    }


@router.post("/avatar/{user_id}")
async def upload_avatar(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File tải lên phải là hình ảnh")

    extension = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"avatar_user_{user_id}_{uuid.uuid4().hex[:8]}{extension}"
    file_path = os.path.join(AVATAR_FOLDER, filename)

    async with aiofiles.open(file_path, "wb") as buffer:
        while content := await file.read(1024 * 1024):
            await buffer.write(content)

    avatar_url = f"http://127.0.0.1:8000/uploads/avatars/{filename}"
    user.avatar = avatar_url

    db.commit()
    db.refresh(user)

    return {
        "message": "Cập nhật ảnh đại diện thành công",
        "avatar": avatar_url,
        "user_id": user_id
    }