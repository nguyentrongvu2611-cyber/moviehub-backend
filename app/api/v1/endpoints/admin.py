from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.watchlist import Watchlist
from app.models.movie_view import MovieView
from app.models.movie import Movie

# Import chính xác 2 schema UserOut và AvatarUpdate
from app.schemas.user import UserOut, AvatarUpdate

router = APIRouter()


# 1. Trả về đúng schema UserOut dành cho Admin (Đã bao gồm avatar)
@router.get("/users", response_model=List[UserOut])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_deleted == False).all()
    return users


# 2. API Cập nhật Avatar dùng AvatarUpdate và trả về UserOut
@router.put("/users/{user_id}/avatar", response_model=UserOut)
def update_user_avatar(
    user_id: int,
    payload: AvatarUpdate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    
    user.avatar = payload.avatar
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/ban")
def toggle_ban_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tài khoản"
        )

    user.is_banned = not user.is_banned

    if user.is_banned:
        user.is_active = False
    else:
        user.is_active = True

    db.commit()
    db.refresh(user)

    return {
        "message": "Đã cập nhật trạng thái tài khoản",
        "is_banned": user.is_banned,
        "is_active": user.is_active
    }


@router.put("/users/{user_id}/soft-delete")
def soft_delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tài khoản"
        )

    user.is_deleted = True
    user.is_active = False

    db.commit()

    return {
        "message": "Đã xóa mềm tài khoản"
    }


@router.delete("/users/{user_id}")
def hard_delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tài khoản"
        )

    db.delete(user)
    db.commit()

    return {
        "message": "Đã xóa vĩnh viễn tài khoản"
    }


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role: str,
    db: Session = Depends(get_db)
):
    valid_roles = [
        "user",
        "moderator",
        "admin"
    ]

    if role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail="Role không hợp lệ"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tài khoản"
        )

    user.role = role

    db.commit()
    db.refresh(user)

    return {
        "message": "Đã cập nhật quyền",
        "role": user.role
    }


@router.put("/users/{user_id}/premium")
def update_premium(
    user_id: int,
    days: int = 30,
    lifetime: bool = False,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tài khoản"
        )

    user.is_premium = True

    if lifetime:
        user.premium_lifetime = True
        user.premium_expired_at = None
    else:
        user.premium_lifetime = False
        now = datetime.now()

        if (
            user.premium_expired_at
            and user.premium_expired_at > now
        ):
            user.premium_expired_at = (
                user.premium_expired_at
                + timedelta(days=days)
            )
        else:
            user.premium_expired_at = (
                now + timedelta(days=days)
            )

    db.commit()
    db.refresh(user)

    return {
        "message": "Đã cập nhật Premium",
        "is_premium": user.is_premium,
        "premium_expired_at": user.premium_expired_at,
        "premium_lifetime": user.premium_lifetime
    }


@router.put("/users/{user_id}/remove-premium")
def remove_premium(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tài khoản"
        )

    user.is_premium = False
    user.premium_lifetime = False
    user.premium_expired_at = None

    db.commit()

    return {
        "message": "Đã tước quyền Premium"
    }


@router.put("/users/{user_id}/streaming")
def update_streaming_settings(
    user_id: int,
    max_screens: int = 1,
    video_quality: str = "1080p",
    ad_free: bool = False,
    can_download: bool = False,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tài khoản"
        )

    valid_quality = [
        "480p",
        "720p",
        "1080p",
        "4K"
    ]

    if video_quality not in valid_quality:
        raise HTTPException(
            status_code=400,
            detail="Chất lượng video không hợp lệ"
        )

    user.max_screens = max_screens
    user.video_quality = video_quality
    user.ad_free = ad_free
    user.can_download = can_download

    db.commit()
    db.refresh(user)

    return {
        "message": "Đã cập nhật quyền xem phim"
    }


@router.put("/users/{user_id}/mute")
def toggle_mute_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tài khoản"
        )

    user.is_muted = not user.is_muted

    db.commit()
    db.refresh(user)

    return {
        "message": "Đã cập nhật trạng thái bình luận",
        "is_muted": user.is_muted
    }


@router.delete("/users/{user_id}/watchlist")
def delete_user_watchlist(
    user_id: int,
    db: Session = Depends(get_db)
):
    db.query(Watchlist).filter(
        Watchlist.user_id == user_id
    ).delete()

    db.commit()

    return {
        "message": "Đã xóa danh sách yêu thích"
    }


@router.delete("/users/{user_id}/history")
def delete_user_history(
    user_id: int,
    db: Session = Depends(get_db)
):
    db.query(MovieView).filter(
        MovieView.user_id == user_id
    ).delete()

    db.commit()

    return {
        "message": "Đã xóa lịch sử xem phim"
    }


@router.get("/users/{user_id}/history")
def get_user_history(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")

    history_records = (
        db.query(MovieView)
        .filter(MovieView.user_id == user_id)
        .order_by(MovieView.watched_at.desc())
        .all()
    )

    result = []
    for item in history_records:
        movie = item.movie if hasattr(item, "movie") and item.movie else None

        result.append({
            "id": item.id,
            "movie_id": item.movie_id,
            "title": movie.title if movie else "Phim không tên",
            "poster_url": movie.poster_url if movie else None,
            "watched_at": item.watched_at.isoformat() if item.watched_at else None
        })

    return result