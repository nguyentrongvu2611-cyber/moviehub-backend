from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.movie import Movie
from app.models.user import User
from app.models.watchlist import Watchlist

router = APIRouter()


@router.get("/{user_id}")
def get_watchlist(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )

    watchlist = db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
    return watchlist


@router.post("/")
def add_to_watchlist(user_id: int, movie_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )

    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy phim"
        )

    exists = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id, Watchlist.movie_id == movie_id)
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phim đã có trong danh sách yêu thích"
        )

    new_watchlist = Watchlist(user_id=user_id, movie_id=movie_id)
    db.add(new_watchlist)
    db.commit()
    db.refresh(new_watchlist)

    return {
        "message": "Đã thêm vào danh sách yêu thích",
        "data": new_watchlist
    }


@router.delete("/{user_id}/{movie_id}")
def remove_from_watchlist(user_id: int, movie_id: int, db: Session = Depends(get_db)):
    watchlist = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id, Watchlist.movie_id == movie_id)
        .first()
    )
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy phim trong danh sách yêu thích"
        )

    db.delete(watchlist)
    db.commit()

    return {"message": "Đã xóa khỏi danh sách yêu thích"}