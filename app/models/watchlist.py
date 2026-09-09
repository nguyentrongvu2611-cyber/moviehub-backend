from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id"),
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="watchlists"
    )

    movie = relationship(
        "Movie",
        back_populates="watchlists"
    )