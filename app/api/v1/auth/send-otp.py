import random
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import bcrypt
from passlib.context import CryptContext

from app.models.user import User  
from app.core.database import get_db
from app.core.config import send_otp_email 
from app.core.security import get_current_user

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bộ nhớ tạm lưu OTP dùng chung cho cả gửi & xác thực
# (Lưu ý: Nếu verify-otp nằm ở file khác, hãy import otp_store từ file chung như app.core.config hoặc app.core.security)
otp_store = {}

class SendOTPRequest(BaseModel):
    user_id: int
    current_password: str
    new_email: EmailStr

@router.post("/send-otp")
async def send_otp_for_email_change(
    data: SendOTPRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Kiểm tra mật khẩu hiện tại (Hỗ trợ linh hoạt cả Bcrypt lẫn Passlib)
    is_password_correct = False
    try:
        is_password_correct = bcrypt.checkpw(
            data.current_password.encode('utf-8'), 
            current_user.password.encode('utf-8')
        )
    except Exception:
        is_password_correct = pwd_context.verify(data.current_password, current_user.password)

    if not is_password_correct:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Mật khẩu hiện tại không chính xác!"
        )

    # 2. Kiểm tra email mới trùng email hiện tại
    clean_email = data.new_email.strip()
    if current_user.email == clean_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email mới phải khác email hiện tại!"
        )

    # 3. Kiểm tra email mới đã tồn tại trên hệ thống chưa
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email này đã được sử dụng bởi một tài khoản khác!"
        )

    # 4. Tạo OTP 6 số ngẫu nhiên & LƯU VÀO OTP_STORE (Hạn dùng 5 phút)
    otp_code = str(random.randint(100000, 999999))
    otp_store[clean_email] = {
        "code": otp_code,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "user_id": current_user.id
    }

    # 5. Gửi Email OTP
    try:
        await send_otp_email(clean_email, otp_code)
    except Exception as e:
        # Nếu gửi mail lỗi thì xóa OTP vừa lưu để dọn dẹp
        if clean_email in otp_store:
            del otp_store[clean_email]
            
        print("❌ Lỗi gửi Mail chi tiết:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi kết nối tới máy chủ gửi mail: {str(e)}"
        )

    return {"message": f"Đã gửi mã OTP thành công tới {clean_email}"}