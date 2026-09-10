import os
import uuid
import json
import asyncio
import aiofiles
import ffmpeg
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from pydantic import BaseModel

from app.core.database import get_db
from app.models.movie import Movie
from app.models.category import Category
from app.models.movie_view import MovieView
from app.models.comment import Comment
from app.schemas.movie import MovieCreate, MovieResponse, MovieUpdate
from app.schemas.comment import CommentCreate, CommentResponse, MovieCommentsSummary
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")

# Tên miền chính thức trên Render (Dùng để fix lỗi Mixed Content HTTP/HTTPS)
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "https://moviehub-backend-ln1c.onrender.com")


class MovieSectionUpdate(BaseModel):
    section_type: str


# ==========================================
# HÀM BỔ TRỢ & FORMAT RESPONSE
# ==========================================

def get_full_media_url(path: Optional[str]) -> Optional[str]:
    """Helper chuyển đổi đường dẫn tương đối hoặc Localhost thành URL Render HTTPS hoàn chỉnh."""
    if not path:
        return path
    if path.startswith("http://127.0.0.1:8000") or path.startswith("http://localhost:8000"):
        return path.replace("http://127.0.0.1:8000", BASE_URL).replace("http://localhost:8000", BASE_URL)
    if path.startswith("/"):
        return f"{BASE_URL}{path}"
    return path


def transcode_video_sync(input_path: str, output_folder: str):
    """Nén video sang 720p và 480p bằng FFmpeg ở background."""
    resolutions = {
        "720p": ("1280x720", "1M"),
        "480p": ("854x480", "500k")
    }
    
    ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"

    for quality, (scale, bitrate) in resolutions.items():
        output_path = os.path.join(output_folder, f"{quality}.mp4")
        try:
            (
                ffmpeg
                .input(input_path)
                .output(output_path, vf=f"scale={scale}", video_bitrate=bitrate, acodec="aac")
                .overwrite_output()
                .run(cmd=ffmpeg_exe, capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            print(f"Lỗi FFmpeg khi render {quality}: {e.stderr.decode('utf-8') if e.stderr else str(e)}")
        except Exception as e:
            print(f"Lỗi hệ thống khi render {quality}: {str(e)}")


async def run_transcode(input_path: str, output_folder: str):
    await asyncio.to_thread(transcode_video_sync, input_path, output_folder)


def format_movie_response(movie: Movie, db: Session) -> dict:
    """Format dữ liệu phim trả về API, tự động bổ sung Full HTTPS URL cho Poster & Video."""
    views_count = db.query(func.count(MovieView.id)).filter(
        MovieView.movie_id == movie.id
    ).scalar() or 0

    # Xử lý video_urls (Đảm bảo đọc đúng dạng dict/json)
    raw_video_urls = getattr(movie, "video_urls", None)
    if isinstance(raw_video_urls, str):
        try:
            raw_video_urls = json.loads(raw_video_urls)
        except Exception:
            raw_video_urls = {}

    if not raw_video_urls and movie.video_url:
        raw_video_urls = {"1080p": movie.video_url}

    # Nối Domain HTTPS cho từng chất lượng phim
    formatted_video_urls = {}
    if isinstance(raw_video_urls, dict):
        for quality, url in raw_video_urls.items():
            formatted_video_urls[quality] = get_full_media_url(url)

    return {
        "id": movie.id,
        "title": movie.title,
        "description": movie.description,
        "year": movie.year,
        "duration": movie.duration,
        "quality": movie.quality,
        "director": getattr(movie, "director", "Chưa cập nhật"),
        "views": views_count,
        "poster_url": get_full_media_url(movie.poster_url),
        "video_url": get_full_media_url(movie.video_url),
        "video_urls": formatted_video_urls,
        "category_id": movie.category_id,
        "is_free": movie.is_free,
        "movie_type": getattr(movie, "movie_type", "single"),
        "country": getattr(movie, "country", "vn"),
        "section_type": getattr(movie, "section_type", "feature"),
    }


# ==========================================
# 1. UPLOAD MEDIA
# ==========================================

@router.post("/upload-video")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith(('.mp4', '.mkv', '.avi', '.mov')):
        raise HTTPException(status_code=400, detail="Định dạng video không hỗ trợ. Hãy chọn file .mp4, .mkv, .avi")

    video_id = str(uuid.uuid4())
    movie_folder = os.path.join(UPLOAD_DIR, "videos", video_id)
    os.makedirs(movie_folder, exist_ok=True)

    original_path = os.path.join(movie_folder, "1080p.mp4")
    try:
        async with aiofiles.open(original_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):
                await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu video gốc: {str(e)}")

    background_tasks.add_task(run_transcode, original_path, movie_folder)

    p_1080 = f"/uploads/videos/{video_id}/1080p.mp4"
    p_720 = f"/uploads/videos/{video_id}/720p.mp4"
    p_480 = f"/uploads/videos/{video_id}/480p.mp4"

    return {
        "message": "Upload video gốc thành công. Đang xử lý nén các bản 720p và 480p ở background...",
        "video_id": video_id,
        "video_url": get_full_media_url(p_1080),
        "video_urls": {
            "1080p": get_full_media_url(p_1080),
            "720p": get_full_media_url(p_720),
            "480p": get_full_media_url(p_480)
        }
    }


@router.post("/upload-poster")
async def upload_poster(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ upload file ảnh (.jpg, .png, .webp)")

    poster_dir = os.path.join(UPLOAD_DIR, "posters")
    os.makedirs(poster_dir, exist_ok=True)

    file_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(poster_dir, file_name)

    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):
                await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu poster: {str(e)}")

    relative_path = f"/uploads/posters/{file_name}"
    return {
        "message": "Upload poster thành công",
        "poster_url": get_full_media_url(relative_path)
    }


# ==========================================
# 2. QUẢN LÝ PHIM (ROUTES TĨNH & TÌM KIẾM)
# ==========================================

@router.get("/search", response_model=list[MovieResponse])
def search_movies(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    movies = db.query(Movie).filter(
        or_(
            Movie.title.ilike(f"%{q}%"),
            Movie.description.ilike(f"%{q}%")
        )
    ).all()

    return [format_movie_response(m, db) for m in movies]


@router.get("", response_model=list[MovieResponse])
@router.get("/", response_model=list[MovieResponse])
def get_movies(
    section_type: Optional[str] = Query(None, description="Lọc theo section_type"),
    category_id: Optional[int] = Query(None, description="Lọc theo ID thể loại"),
    year: Optional[int] = Query(None, description="Lọc theo năm phát hành"),
    is_free: Optional[bool] = Query(None, description="Lọc phim miễn phí/VIP"),
    movie_type: Optional[str] = Query(None, description="Lọc loại phim (single/series)"),
    country: Optional[str] = Query(None, description="Lọc theo quốc gia"),
    q: Optional[str] = Query(None, description="Từ khóa tìm kiếm"),
    db: Session = Depends(get_db)
):
    query = db.query(Movie)
    
    if movie_type:
        query = query.filter(Movie.movie_type == movie_type)
    if country:
        query = query.filter(Movie.country == country)
    if section_type:
        query = query.filter(Movie.section_type == section_type)
    if category_id:
        query = query.filter(Movie.category_id == category_id)
    if year:
        query = query.filter(Movie.year == year)
    if is_free is not None:
        query = query.filter(Movie.is_free == is_free)
    if q and q.strip():
        search_kw = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Movie.title.ilike(search_kw),
                Movie.description.ilike(search_kw)
            )
        )
        
    movies = query.order_by(Movie.id.desc()).all()
    return [format_movie_response(m, db) for m in movies]


@router.post("", response_model=MovieResponse)
@router.post("/", response_model=MovieResponse)
def create_movie(
    movie: MovieCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = db.query(Category).filter(Category.id == movie.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Không tìm thấy thể loại")

    video_urls = movie.video_urls
    if not video_urls and movie.video_url:
        video_urls = {"1080p": movie.video_url}

    new_movie = Movie(
        title=movie.title,
        description=movie.description,
        year=movie.year,
        duration=movie.duration,
        quality=movie.quality,
        director=movie.director,
        poster_url=movie.poster_url,
        video_url=movie.video_url,
        video_urls=video_urls,
        category_id=movie.category_id,
        is_free=movie.is_free,
        movie_type=movie.movie_type or "single",
        country=movie.country or "vn",
        section_type=movie.section_type or "feature"
    )

    db.add(new_movie)
    db.commit()
    db.refresh(new_movie)

    return format_movie_response(new_movie, db)


# ==========================================
# 3. CÁC ROUTE NHẬN THAM SỐ {movie_id}
# ==========================================

@router.get("/{movie_id}", response_model=MovieResponse)
def get_movie_detail(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Không tìm thấy phim")
    
    return format_movie_response(movie, db)


@router.put("/{movie_id}", response_model=MovieResponse)
def update_movie(
    movie_id: int,
    movie_data: MovieUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Không tìm thấy phim")

    update_data = movie_data.model_dump(exclude_unset=True)

    if "category_id" in update_data and update_data["category_id"] is not None:
        category = db.query(Category).filter(Category.id == update_data["category_id"]).first()
        if not category:
            raise HTTPException(status_code=404, detail="Không tìm thấy thể loại")

    if "video_url" in update_data and "video_urls" not in update_data:
        if update_data["video_url"]:
            update_data["video_urls"] = {"1080p": update_data["video_url"]}

    for field, value in update_data.items():
        setattr(movie, field, value)

    db.commit()
    db.refresh(movie)

    return format_movie_response(movie, db)


@router.patch("/{movie_id}", response_model=MovieResponse)
def update_movie_section(
    movie_id: int,
    data: MovieSectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Không tìm thấy phim")

    movie.section_type = data.section_type
    db.commit()
    db.refresh(movie)

    return format_movie_response(movie, db)


@router.delete("/{movie_id}")
def delete_movie(
    movie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Không tìm thấy phim")

    db.delete(movie)
    db.commit()

    return {"message": "Xóa phim thành công"}


# ==========================================
# 4. BÌNH LUẬN & ĐÁNH GIÁ (COMMENTS & RATINGS)
# ==========================================

@router.get("/{movie_id}/comments", response_model=MovieCommentsSummary)
@router.get("/{movie_id}/comments/", response_model=MovieCommentsSummary)
def get_movie_comments(
    movie_id: int,
    db: Session = Depends(get_db)
):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Không tìm thấy phim")

    comments = db.query(Comment).filter(Comment.movie_id == movie_id).order_by(Comment.id.desc()).all()
    total_ratings = len(comments)
    avg_rating = sum(c.rating for c in comments) / total_ratings if total_ratings > 0 else 0.0

    return {
        "avg_rating": round(avg_rating, 1),
        "total_ratings": total_ratings,
        "comments": comments
    }


@router.post("/{movie_id}/comments", response_model=CommentResponse)
@router.post("/{movie_id}/comments/", response_model=CommentResponse)
def create_movie_comment(
    movie_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Không tìm thấy phim")

    new_comment = Comment(
        movie_id=movie_id,
        user_id=current_user.id,
        username=getattr(current_user, "username", "Người dùng"),
        avatar=getattr(current_user, "avatar", None),
        content=data.content,
        rating=data.rating
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return new_comment


@router.put("/{movie_id}/comments/{comment_id}", response_model=CommentResponse)
@router.put("/{movie_id}/comments/{comment_id}/", response_model=CommentResponse)
def update_movie_comment(
    movie_id: int,
    comment_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment = db.query(Comment).filter(
        Comment.id == comment_id, 
        Comment.movie_id == movie_id,
        Comment.user_id == current_user.id
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bình luận hoặc bạn không có quyền sửa")

    comment.content = data.content
    comment.rating = data.rating

    db.commit()
    db.refresh(comment)

    return comment


@router.delete("/{movie_id}/comments/{comment_id}")
@router.delete("/{movie_id}/comments/{comment_id}/")
def delete_movie_comment(
    movie_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment = db.query(Comment).filter(
        Comment.id == comment_id, 
        Comment.movie_id == movie_id,
        Comment.user_id == current_user.id
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bình luận hoặc bạn không có quyền xóa")

    db.delete(comment)
    db.commit()

    return {"message": "Xóa bình luận thành công"}