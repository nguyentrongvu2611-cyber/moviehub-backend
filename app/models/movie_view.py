from datetime import datetime
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class MovieView(Base):
    __tablename__ = "movie_views"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id"),
        nullable=False
    )

    watched_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Khai báo Relationship (Chỉ giữ 1 biến user và 1 biến movie)
    user = relationship("User", back_populates="movie_views")
    movie = relationship("Movie", back_populates="movie_views")