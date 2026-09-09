from typing import Optional, Dict
from pydantic import BaseModel, Field
from app.schemas.category import CategoryResponse

class MovieBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Tên phim")
    description: str = Field(..., min_length=1, description="Mô tả phim")
    year: int = Field(..., ge=1888, le=2100, description="Năm sản xuất")
    duration: int = Field(..., ge=1, description="Thời lượng (phút)")
    quality: str = Field(default="1080p", min_length=1, max_length=20)
    director: Optional[str] = Field(default="Chưa cập nhật", max_length=255)
    poster_url: Optional[str] = None
    video_url: Optional[str] = None
    
    # THÊM ĐỊNH NGHĨA CHẤT LƯỢNG VIDEO
    video_urls: Optional[Dict[str, str]] = None

    category_id: int = Field(..., description="ID danh mục phim")
    is_free: bool = True

    # Các trường mở rộng
    movie_type: Optional[str] = Field(default="single", description="Loại phim: single/series")
    country: Optional[str] = Field(default="vn", description="Quốc gia phát hành")
    section_type: Optional[str] = Field(default="feature", description="Vị trí hiển thị trên giao diện")

class MovieCreate(MovieBase):
    pass

class MovieUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    year: Optional[int] = Field(None, ge=1888, le=2100)
    duration: Optional[int] = Field(None, ge=1)
    quality: Optional[str] = Field(None, min_length=1, max_length=20)
    director: Optional[str] = Field(None, max_length=255)
    poster_url: Optional[str] = None
    video_url: Optional[str] = None
    
    # CHO PHÉP CẬP NHẬT VIDEO_URLS
    video_urls: Optional[Dict[str, str]] = None

    category_id: Optional[int] = None
    is_free: Optional[bool] = None
    movie_type: Optional[str] = None
    country: Optional[str] = None
    section_type: Optional[str] = None

class MovieResponse(MovieBase):
    id: int
    views: int = 0
    category: Optional[CategoryResponse] = None

    model_config = {
        "from_attributes": True
    }