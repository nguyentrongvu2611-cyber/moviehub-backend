import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Ưu tiên lấy DATABASE_URL từ biến môi trường Render, nếu không có mới dùng localhost ở máy cá nhân
DEFAULT_LOCAL_DB = "postgresql://postgres:123456@localhost:5433/moviehub"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_LOCAL_DB)

# Render trả về chuỗi postgres:// nhưng SQLAlchemy 2.0 yêu cầu postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()