from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.movie import Movie
from app.models.user import User

router = APIRouter()

ACTIVE_SESSIONS: Dict[int, Dict[str, datetime]] = {}


# --- 1. API KIỂM TRA QUYỀN XEM PHIM (PREMIUM CHECK) ---
@router.get("/check-access/{user_id}/{movie_id}")
def check_movie_access(
    user_id: int, 
    movie_id: int, 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại")

    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Bộ phim không tồn tại")

    now = datetime.utcnow()
    
    # Kiểm tra xem User có Premium còn hạn hay không
    is_premium_user = bool(
        user.is_premium and 
        user.premium_expired_at and 
        user.premium_expired_at > now
    )

    # Nếu phim yêu cầu Premium mà user không phải Premium
    if getattr(movie, "is_premium", False) and not is_premium_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phim này dành riêng cho gói Premium. Vui lòng nâng cấp tài khoản để xem!"
        )

    return {
        "status": "allowed",
        "message": "Có quyền xem phim",
        "is_premium": is_premium_user
    }


# --- 2. API PING GIỮ PHIÊN XEM PHIM & GIỚI HẠN MÀN HÌNH ---
@router.post("/ping/{user_id}/{session_id}")
def ping_stream(user_id: int, session_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User không tồn tại")

    now = datetime.utcnow()
    
    # Kiểm tra tài khoản Premium còn hạn hay không
    is_premium_active = bool(
        user.is_premium and 
        user.premium_expired_at and 
        user.premium_expired_at > now
    )

    # Nếu còn hạn Premium thì lấy max_screens lưu trong DB (2, 3 hoặc 11)
    # Nếu không phải Premium hoặc hết hạn thì mặc định là 1 màn hình
    max_screens = (user.max_screens if is_premium_active else 1) or 1

    if user_id not in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS[user_id] = {}

    # Dọn dẹp phiên hết hạn (> 3 giây không ping)
    expired_sessions = [
        s_id for s_id, last_ping in ACTIVE_SESSIONS[user_id].items()
        if (now - last_ping).total_seconds() > 3
    ]
    for s_id in expired_sessions:
        del ACTIVE_SESSIONS[user_id][s_id]

    # Kiểm tra giới hạn số màn hình đang xem cùng lúc
    if session_id not in ACTIVE_SESSIONS[user_id]:
        if len(ACTIVE_SESSIONS[user_id]) >= max_screens:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản của bạn đã đạt giới hạn tối đa {max_screens} màn hình xem cùng lúc!"
            )

    ACTIVE_SESSIONS[user_id][session_id] = now
    return {
        "status": "ok", 
        "active_screens": len(ACTIVE_SESSIONS[user_id]),
        "max_screens": max_screens
    }


# --- 3. API HỦY PHIÊN KHI TẮT TAB / CHUYỂN TRANG (HỖ TRỢ CẢ POST VÀ DELETE) ---
@router.api_route("/leave/{user_id}/{session_id}", methods=["POST", "DELETE"])
def leave_stream(user_id: int, session_id: str):
    if user_id in ACTIVE_SESSIONS and session_id in ACTIVE_SESSIONS[user_id]:
        del ACTIVE_SESSIONS[user_id][session_id]
    return {"status": "left"}