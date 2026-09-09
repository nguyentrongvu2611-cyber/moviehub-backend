import random
import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from dotenv import load_dotenv
import json
import asyncio
from pydantic import BaseModel
from app.core.database import get_db
from app.core.sse import sse_manager
from app.core.security import get_current_user, create_access_token
from app.models.user import User
from app.schemas.user import (
    UserLogin,
    UserCreate,
    UserResponse,
    ChangePassword,
    ForgotPassword,
    ResetPassword,
    SendOTPRequest,
    VerifyOTPChangeEmailRequest
)

load_dotenv()

router = APIRouter()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# Cấu hình FastMail kết nối Google SMTP
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

# Bộ nhớ tạm lưu OTP
otp_store = {}


# ==========================================
# 1. ĐĂNG NHẬP, ĐĂNG XUẤT VỚI HTTPONLY COOKIE
# ==========================================
@router.post("/login")
def login(
    user_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == user_data.username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")

    try:
        is_valid_password = pwd_context.verify(user_data.password, user.password)
    except Exception as e:
        print(f"Lỗi kiểm tra bcrypt: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Lỗi hệ thống khi kiểm tra mật khẩu."
        )

    if not is_valid_password:
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khóa")

    access_token = create_access_token(subject=user.id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False  # Đổi thành True khi lên Production (HTTPS)
    )

    return {
        "message": "Đăng nhập thành công",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": getattr(user, "avatar", None),
            "full_name": getattr(user, "full_name", getattr(user, "name", None)),
            "role": user.role,
            "is_active": user.is_active,
            "is_premium": user.is_premium
        }
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Đăng xuất thành công"}

# 2. BẢO MẬT: THAY ĐỔI EMAIL VỚI TOKEN & OTP
@router.post("/send-otp")
async def send_otp_for_email_change(
    data: SendOTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not pwd_context.verify(data.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không chính xác")
    new_email = data.new_email.strip()
    if current_user.email == new_email:
        raise HTTPException(status_code=400, detail="Email mới phải khác với email hiện tại")
    existing_user = db.query(User).filter(User.email == new_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email này đã được sử dụng bởi tài khoản khác")
    otp = str(random.randint(100000, 999999))
    # Cập nhật dùng UTC timezone chuẩn
    otp_store[new_email] = {
        "code": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "user_id": current_user.id
    }
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #141414; color: #ffffff;">
        <h2 style="color: #e50914;">MOVIEHUB</h2>
        <p>Mã xác nhận (OTP) để thay đổi địa chỉ email của bạn là:</p>
        <h1 style="color: #e50914; letter-spacing: 5px; background: #222; padding: 10px; display: inline-block;">{otp}</h1>
        <p>Mã có hiệu lực trong <b>5 phút</b>. Vui lòng không chia sẻ mã này cho bất kỳ ai.</p>
    </div>"""
    message = MessageSchema(
        subject="[MovieHub] Mã OTP Thay đổi địa chỉ Email",
        recipients=[new_email],
        body=html_content,
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)
    return {"message": f"Mã OTP đã được gửi đến email {new_email}"}


@router.post("/verify-otp-change-email")
def verify_otp_and_change_email(
    data: VerifyOTPChangeEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    email_key = data.new_email.strip()
    record = otp_store.get(email_key)

    if not record:
        raise HTTPException(status_code=400, detail="Chưa gửi mã OTP hoặc yêu cầu không hợp lệ!")

    if datetime.now(timezone.utc) > record["expires_at"]:
        del otp_store[email_key]
        raise HTTPException(status_code=400, detail="Mã OTP đã hết hạn, vui lòng nhấn gửi lại mã!")

    if record["code"] != data.otp.strip():
        raise HTTPException(status_code=400, detail="Mã OTP không chính xác!")

    if record["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Xác thực không hợp lệ cho tài khoản này!")

    current_user.email = email_key
    db.commit()

    del otp_store[email_key]

    return {
        "message": "Đổi email thành công!",
        "new_email": current_user.email
    }


# ==========================================
# 3. ĐỔI MẬT KHẨU (KHI ĐÃ ĐĂNG NHẬP)
# ==========================================
@router.post("/change-password")
def change_password(
    data: ChangePassword,  
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not pwd_context.verify(data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Mật khẩu hiện tại không chính xác"
        )
        
    current_user.password = pwd_context.hash(data.new_password)
    db.commit()
    
    return {"message": "Đổi mật khẩu thành công"}


# ==========================================
# 4. CÁC API KHÁC (ĐĂNG KÝ, QUÊN MẬT KHẨU, SSE)
# ==========================================
@router.post("/register", response_model=UserResponse)
def register(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    existing_user = (
        db.query(User)
        .filter((User.username == user.username) | (User.email == user.email))
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Tên đăng nhập hoặc email đã tồn tại"
        )

    hashed_password = pwd_context.hash(user.password)

    new_user = User(
        username=user.username,
        email=user.email,
        password=hashed_password,
        role="user",
        is_active=True,
        is_premium=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPassword,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="Email không tồn tại trong hệ thống")

    otp = str(random.randint(100000, 999999))

    otp_store[data.email] = {
        "code": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)
    }

    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #141414; color: #ffffff;">
        <h2 style="color: #e50914;">MOVIEHUB</h2>
        <p>Mã xác nhận (OTP) để đặt lại mật khẩu của bạn là:</p>
        <h1 style="color: #e50914; letter-spacing: 5px; background: #222; padding: 10px; display: inline-block;">{otp}</h1>
        <p>Mã có hiệu lực trong <b>5 phút</b>. Vui lòng không chia sẻ mã này cho ai.</p>
    </div>
    """

    message = MessageSchema(
        subject="[MovieHub] Mã OTP Đặt lại mật khẩu",
        recipients=[data.email],
        body=html_content,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)

    return {"message": "Mã OTP đã được gửi về email của bạn"}


@router.post("/reset-password")
def reset_password(
    data: ResetPassword,
    db: Session = Depends(get_db)
):
    record = otp_store.get(data.email)
    if not record:
        raise HTTPException(status_code=400, detail="Chưa có yêu cầu mã OTP cho email này")

    if datetime.now(timezone.utc) > record["expires_at"]:
        del otp_store[data.email]
        raise HTTPException(status_code=400, detail="Mã OTP đã hết hạn")

    if record["code"] != data.otp:
        raise HTTPException(status_code=400, detail="Mã OTP không chính xác")

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")

    user.password = pwd_context.hash(data.password)
    db.commit()

    del otp_store[data.email]

    return {"message": "Đặt lại mật khẩu thành công"}


@router.get("/stream/{user_id}")
async def stream_user_events(user_id: int, request: Request):
    async def event_generator():
        queue = await sse_manager.connect(user_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            sse_manager.disconnect(user_id, queue)
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"})


@router.put("/admin/users/{user_id}/status")
async def update_user_status(
    user_id: int, 
    is_premium: bool, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Bổ sung kiểm tra Authentication
):
    # Kiểm tra phân quyền Admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền thực hiện thao tác này")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    user.is_premium = is_premium
    if not is_premium:
        user.premium_expired_at = None
        user.role = "user"
    
    db.commit()

    await sse_manager.send_event(
        user_id=user_id,
        event_type="USER_STATUS_UPDATED",
        data={
            "is_premium": user.is_premium,
            "role": user.role,
            "message": "Trạng thái tài khoản của bạn đã được cập nhật!"
        }
    )

    return {"message": "Cập nhật thành công"}

class UpdateNameRequest(BaseModel):
    full_name: str
    
@router.put("/users/me")
def update_user_name(
    data: UpdateNameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not data.full_name.strip():
        raise HTTPException(status_code=400, detail="Tên hiển thị không được để trống")

    current_user.full_name = data.full_name.strip()
    db.commit()
    db.refresh(current_user)

    return {
        "message": "Cập nhật tên thành công",
        "full_name": current_user.full_name
    }