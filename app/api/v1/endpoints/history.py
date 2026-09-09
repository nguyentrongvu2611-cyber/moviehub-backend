from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.user import User
from app.models.movie import Movie
from app.models.movie_view import MovieView

router = APIRouter()


@router.get("/user/{user_id}")
def get_user_history(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    history_records = (
        db.query(MovieView)
        .options(joinedload(MovieView.movie))
        .filter(MovieView.user_id == user_id)
        .order_by(MovieView.watched_at.desc())
        .all()
    )

    result = []
    for item in history_records:
        movie = item.movie
        result.append({
            "id": item.id,
            "movie_id": movie.id if movie else item.movie_id,
            "title": movie.title if movie else "Phim không tên",
            "poster_url": movie.poster_url if movie else None,
            "watched_at": item.watched_at.isoformat() if item.watched_at else None
        })

    return result


@router.post("/watch/{user_id}/{movie_id}")
def add_movie_view(user_id: int, movie_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Không tìm thấy phim")

    movie_view = MovieView(user_id=user_id, movie_id=movie_id)
    db.add(movie_view)
    db.commit()
    db.refresh(movie_view)

    return {"message": "Đã lưu lịch sử xem phim"}