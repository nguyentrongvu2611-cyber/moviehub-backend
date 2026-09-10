import json
from typing import Optional, Dict, Union
from pydantic import BaseModel, Field, field_validator
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
    
    # Hỗ trợ nhận cả Dict lẫn chuỗi JSON
    video_urls: Optional[Union[Dict[str, str], str]] = None

    category_id: int = Field(..., description="ID danh mục phim")
    is_free: bool = True

    movie_type: Optional[str] = Field(default="single", description="Loại phim: single/series")
    country: Optional[str] = Field(default="vn", description="Quốc gia phát hành")
    section_type: Optional[str] = Field(default="feature", description="Vị trí hiển thị trên giao diện")

    @field_validator("video_urls", mode="before")
    @classmethod
    def parse_video_urls(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return {}
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v or {}


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
    video_urls: Optional[Union[Dict[str, str], str]] = None

    category_id: Optional[int] = None
    is_free: Optional[bool] = None
    movie_type: Optional[str] = None
    country: Optional[str] = None
    section_type: Optional[str] = None

    @field_validator("video_urls", mode="before")
    @classmethod
    def parse_video_urls(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return {}
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v


class MovieResponse(MovieBase):
    id: int
    views: int = 0
    category: Optional[CategoryResponse] = None

    model_config = {
        "from_attributes": True
    }