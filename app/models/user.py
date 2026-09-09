from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False
    )

    # Bổ sung trường avatar (Dùng Text để lưu được cả chuỗi Base64 dài hoặc URL)
    avatar: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="user"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    is_banned: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_premium: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    premium_expired_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    premium_lifetime: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    max_screens: Mapped[int] = mapped_column(
        Integer,
        default=1
    )

    video_quality: Mapped[str] = mapped_column(
        String(20),
        default="1080p"
    )

    ad_free: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    can_download: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_muted: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    watchlists = relationship(
        "Watchlist",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    payments = relationship(
        "Payment",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    movie_views = relationship(
        "MovieView",
        back_populates="user",
        cascade="all, delete-orphan"
    )