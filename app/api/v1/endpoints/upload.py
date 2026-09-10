import os
import uuid
import aiofiles

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User

router = APIRouter()

UPLOAD_FOLDER = "uploads"
POSTER_FOLDER = os.path.join(UPLOAD_FOLDER, "posters")
VIDEO_FOLDER = os.path.join(UPLOAD_FOLDER, "videos")
AVATAR_FOLDER = os.path.join(UPLOAD_FOLDER, "avatars")

os.makedirs(POSTER_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(AVATAR_FOLDER, exist_ok=True)


@router.post("/poster")
async def upload_poster(file: UploadFile = File(...)):
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
async def upload_video(file: UploadFile = File(...)):
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File phải là video")

    extension = os.path.splitext(file.filename)[1] or ".mp4"
    filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(VIDEO_FOLDER, filename)

    try:
        async with aiofiles.open(file_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):
                await buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu video: {str(e)}")

    video_url = f"/uploads/videos/{filename}"

    return {
        "url": video_url,
        "video_url": video_url,
        "file_path": video_url
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

    avatar_url = f"https://moviehub-backend-ln1c.onrender.com/uploads/avatars/{filename}"
    user.avatar = avatar_url

    db.commit()
    db.refresh(user)

    return {
        "message": "Cập nhật ảnh đại diện thành công",
        "avatar": avatar_url,
        "user_id": user_id
    }
    
@router.get("/stream-progress")
async def get_stream_progress():
    return {
        "status": "success",
        "progress": 100,
        "message": "Sẵn sàng xử lý file"
    }