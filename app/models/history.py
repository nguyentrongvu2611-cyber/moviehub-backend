from datetime import datetime
from sqlalchemy import Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class WatchHistory(Base):
    __tablename__ = "watch_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    watched_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user = relationship("User", back_populates="history")
    movie = relationship("Movie", back_populates="history")