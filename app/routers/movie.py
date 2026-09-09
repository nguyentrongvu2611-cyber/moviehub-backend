import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/movies",
    tags=["Movies"]
)

# Thư mục gốc lưu trữ videos
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "videos")


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Kiểm tra quyền Admin trước khi cho phép upload
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Bạn không có quyền upload video"
        )

    # 1. Tạo UUID làm tên thư mục duy nhất cho video này
    video_id = str(uuid.uuid4())
    movie_folder = os.path.join(UPLOAD_DIR, video_id)
    os.makedirs(movie_folder, exist_ok=True)

    # 2. Định nghĩa file video (ví dụ mặc định lưu là 1080p.mp4)
    file_extension = os.path.splitext(file.filename)[1] or ".mp4"
    file_name = f"1080p{file_extension}"
    file_path = os.path.join(movie_folder, file_name)

    # 3. Ghi file trực tiếp vào thư mục vừa tạo
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu file: {str(e)}")

    # 4. Trả về đường dẫn tĩnh đã lưu
    relative_path = f"/uploads/videos/{video_id}/{file_name}"
    
    return {
        "message": "Upload video thành công!",
        "video_id": video_id,
        "video_url": relative_path
    }