from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    plan: Mapped[str] = mapped_column(
        String(50)
    )

    amount: Mapped[int] = mapped_column(
        Integer
    )

    months: Mapped[int] = mapped_column(
        Integer
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="payments"
    )