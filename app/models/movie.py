from sqlalchemy import String, Text, Integer, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Cột lưu dictionary dạng JSON {"480p": "...", "720p": "...", "1080p": "..."}
    video_urls: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    quality: Mapped[str] = mapped_column(String(20), nullable=False, default="1080p")
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    director: Mapped[str | None] = mapped_column(String(255), nullable=True, default="Chưa cập nhật")
    
    views: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    
    section_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default="feature")
    movie_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default="single")
    country: Mapped[str | None] = mapped_column(String(50), nullable=True, default="vn")

    # Relationships
    category = relationship("Category", back_populates="movies")
    watchlists = relationship("Watchlist", back_populates="movie", cascade="all, delete-orphan")
    movie_views = relationship("MovieView", back_populates="movie", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="movie", cascade="all, delete-orphan")