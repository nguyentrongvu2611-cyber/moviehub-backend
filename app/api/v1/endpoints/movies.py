import os
import uuid
import json
import aiofiles
from typing import Optional, List, Dict, Union
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
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


def prepare_video_urls(video_urls_input: Optional[Union[Dict[str, str], str]]) -> Dict[str, str]:
    """Chuyển đổi dữ liệu video_urls từ string/dict thành dict chuẩn."""
    if not video_urls_input:
        return {}
    if isinstance(video_urls_input, str):
        try:
            parsed = json.loads(video_urls_input)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    if isinstance(video_urls_input, dict):
        return video_urls_input
    return {}


def format_movie_response(movie: Movie, db: Session) -> dict:
    """Format dữ liệu phim trả về API, tự động bổ sung Full HTTPS URL cho Poster & Video."""
    views_count = db.query(func.count(MovieView.id)).filter(
        MovieView.movie_id == movie.id
    ).scalar() or 0

    # Xử lý chuẩn hóa video_urls từ model
    raw_video_urls = prepare_video_urls(getattr(movie, "video_urls", None))

    if not raw_video_urls and movie.video_url:
        raw_video_urls = {"1080p": movie.video_url}

    # Nối Domain HTTPS cho từng chất lượng phim
    formatted_video_urls = {}
    for quality, url in raw_video_urls.items():
        if url:
            formatted_video_urls[quality] = get_full_media_url(str(url))

    # Tự động gán video_url mặc định nếu thiếu
    default_video_url = (
        formatted_video_urls.get("1080p") or
        formatted_video_urls.get("720p") or
        formatted_video_urls.get("480p") or
        get_full_media_url(movie.video_url)
    )

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
        "video_url": default_video_url,
        "video_urls": formatted_video_urls,
        "category_id": movie.category_id,
        "is_free": movie.is_free,
        "movie_type": getattr(movie, "movie_type", "single"),
        "country": getattr(movie, "country", "vn"),
        "section_type": getattr(movie, "section_type", "feature"),
    }


# ==========================================
# 1. UPLOAD MEDIA (ĐÃ TỐI ƯU MULTI-QUALITY)
# ==========================================

@router.post("/upload-video")
async def upload_video(
    file_480p: Optional[UploadFile] = File(None),
    file_720p: Optional[UploadFile] = File(None),
    file_1080p: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    """
    Nhận trực tiếp tối đa 3 chất lượng file video đã được convert sẵn từ client.
    Không tốn tài nguyên transcode server.
    """
    files = {
        "480p": file_480p,
        "720p": file_720p,
        "1080p": file_1080p
    }

    if not any(files.values()):
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp ít nhất 1 file video (480p, 720p hoặc 1080p).")

    video_id = str(uuid.uuid4())
    movie_folder = os.path.join(UPLOAD_DIR, "videos", video_id)
    os.makedirs(movie_folder, exist_ok=True)

    video_urls = {}

    for quality, file_obj in files.items():
        if file_obj:
            ext = os.path.splitext(file_obj.filename)[1].lower() or ".mp4"
            if ext not in ['.mp4', '.mkv', '.avi', '.mov']:
                raise HTTPException(status_code=400, detail=f"Định dạng {ext} của file {quality} không được hỗ trợ.")

            file_path = os.path.join(movie_folder, f"{quality}{ext}")
            try:
                async with aiofiles.open(file_path, 'wb') as out_file:
                    while chunk := await file_obj.read(1024 * 1024):
                        await out_file.write(chunk)
                
                rel_path = f"/uploads/videos/{video_id}/{quality}{ext}"
                video_urls[quality] = get_full_media_url(rel_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Lỗi khi lưu file {quality}: {str(e)}")

    default_url = video_urls.get("1080p") or video_urls.get("720p") or video_urls.get("480p")

    return {
        "message": "Upload các bản chất lượng phim thành công!",
        "video_id": video_id,
        "video_url": default_url,
        "video_urls": video_urls
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
            while chunk := await file.read(1024 * 1024):
                await out_file.write(chunk)
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

@router.get("/search", response_model=List[MovieResponse])
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


@router.get("", response_model=List[MovieResponse])
@router.get("/", response_model=List[MovieResponse])
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

    # Chuẩn hóa video_urls
    video_urls = prepare_video_urls(movie.video_urls)
    if not video_urls and movie.video_url:
        video_urls = {"1080p": movie.video_url}

    default_video_url = movie.video_url or video_urls.get("1080p") or video_urls.get("720p") or video_urls.get("480p")

    new_movie = Movie(
        title=movie.title,
        description=movie.description,
        year=movie.year,
        duration=movie.duration,
        quality=movie.quality,
        director=movie.director,
        poster_url=movie.poster_url,
        video_url=default_video_url,
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

    update_dict = movie_data.model_dump(exclude_unset=True)

    if "category_id" in update_dict and update_dict["category_id"] is not None:
        category = db.query(Category).filter(Category.id == update_dict["category_id"]).first()
        if not category:
            raise HTTPException(status_code=404, detail="Không tìm thấy thể loại")

    if "video_urls" in update_dict:
        update_dict["video_urls"] = prepare_video_urls(update_dict["video_urls"])

    if update_dict.get("video_url") and not update_dict.get("video_urls"):
        update_dict["video_urls"] = {"1080p": update_dict["video_url"]}

    for field, value in update_dict.items():
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