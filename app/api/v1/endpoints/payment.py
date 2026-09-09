import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.payment import Payment
from app.models.user import User

router = APIRouter()

# Helper lấy thời gian hiện tại chuẩn giờ Việt Nam
def get_vn_now():
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

PLANS = {
    "1month": {"amount": 99000, "months": 1},
    "6months": {"amount": 399000, "months": 6},
    "12months": {"amount": 699000, "months": 12}
}

PLAN_SCREENS = {
    "1month": 2,
    "6months": 3,
    "12months": 11,
}

class PaymentCreateRequest(BaseModel):
    user_id: int
    plan: str


@router.post("/")
def create_payment(payload: PaymentCreateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    if payload.plan not in PLANS:
        raise HTTPException(status_code=400, detail="Gói Premium không hợp lệ")

    plan_data = PLANS[payload.plan]
    payment = Payment(
        user_id=payload.user_id,
        plan=payload.plan,
        amount=plan_data["amount"],
        months=plan_data["months"],
        status="pending"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {"message": "Yêu cầu thanh toán đang chờ xử lý", "payment_id": payment.id}


@router.get("/check-status/{user_id}")
def check_payment_status(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    latest_payment = (
        db.query(Payment)
        .filter(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .first()
    )

    now = get_vn_now()
    is_premium = False

    if user.is_premium:
        if getattr(user, "premium_lifetime", False):
            is_premium = True
        elif user.premium_expired_at:
            # Ép múi giờ về Việt Nam để so sánh
            exp_date = user.premium_expired_at
            if exp_date.tzinfo is None:
                exp_date = exp_date.replace(tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
            if exp_date > now:
                is_premium = True

    return {
        "is_premium": is_premium,
        "premium_lifetime": getattr(user, "premium_lifetime", False),
        "latest_payment_status": latest_payment.status if latest_payment else None,
        "latest_payment_id": latest_payment.id if latest_payment else None,
        "premium_expired_at": user.premium_expired_at.isoformat() if user.premium_expired_at else None,
        "user": {
            "id": user.id,
            "is_premium": is_premium,
            "max_screens": getattr(user, "max_screens", 2),
            "premium_expired_at": user.premium_expired_at.isoformat() if user.premium_expired_at else None
        }
    }


@router.put("/{payment_id}/approve")
def approve_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")

    if payment.status == "approved":
        raise HTTPException(status_code=400, detail="Giao dịch đã được xác nhận")

    user = db.query(User).filter(User.id == payment.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    now = get_vn_now()
    start_date = now

    # Nếu user còn hạn Premium thì tính nối tiếp, nếu không hoặc hạn cũ nằm ở tương lai vô lý thì tính từ hiện tại
    if user.premium_expired_at:
        exp_date = user.premium_expired_at
        if exp_date.tzinfo is None:
            exp_date = exp_date.replace(tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
        if exp_date > now and exp_date < now + timedelta(days=365 * 2): # Chống bug dồn năm vô lý
            start_date = exp_date

    user.is_premium = True
    user.premium_expired_at = start_date + timedelta(days=payment.months * 30)
    user.max_screens = PLAN_SCREENS.get(payment.plan, 2)
    payment.status = "approved"

    db.commit()
    db.refresh(user)

    return {
        "message": "Đã kích hoạt Premium",
        "premium_expired_at": user.premium_expired_at.isoformat(),
        "user": {
            "id": user.id,
            "is_premium": True,
            "max_screens": user.max_screens,
            "premium_expired_at": user.premium_expired_at.isoformat()
        }
    }


@router.post("/webhook")
async def bank_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    content = str(data.get("content", "")).upper()
    match = re.search(r"MOVIEHUB(12T|6T)?\s*0*(\d+)", content)
    if not match: return {"status": "ignored", "reason": "Nội dung chuyển khoản không hợp lệ"}
    prefix_plan = match.group(1)
    user_id = int(match.group(2))
    plan_mapping = {"12T": "12months", "6T": "6months"}
    selected_plan = plan_mapping.get(prefix_plan, "1month")
    user = db.query(User).filter(User.id == user_id).first()
    if not user: return {"status": "error", "reason": f"Không tìm thấy user {user_id}"}
    payment = (db.query(Payment)
        .filter(Payment.user_id == user_id, Payment.status == "pending")
        .order_by(Payment.created_at.desc()).first())
    if not payment:
        payment = Payment(user_id=user_id,plan=selected_plan,
            amount=PLANS[selected_plan]["amount"],
            months=PLANS[selected_plan]["months"],
            status="pending")
        db.add(payment)
        db.flush()
    now = get_vn_now()
    start_date = now
    if user.is_premium and user.premium_expired_at:
        exp_date = user.premium_expired_at
        if exp_date.tzinfo is None:
            exp_date = exp_date.replace(tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
        if exp_date > now:
            start_date = exp_date
    user.is_premium = True
    user.premium_expired_at = start_date + timedelta(days=payment.months * 30)
    user.max_screens = max(getattr(user, "max_screens", 2) or 2, PLAN_SCREENS.get(selected_plan, 2))
    payment.status = "approved"
    db.commit()
    return {
        "status": "success",
        "message": f"Kích hoạt thành công gói {selected_plan} cho User {user_id}"}