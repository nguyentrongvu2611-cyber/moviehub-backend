from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# Request Đăng ký tài khoản
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập")
    email: EmailStr
    password: str = Field(..., min_length=6, description="Mật khẩu tối thiểu 6 ký tự")


# Request Đăng nhập
class UserLogin(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


# Response Trả về thông tin User cơ bản
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    is_banned: bool
    is_premium: bool
    avatar: Optional[str] = None  

    class Config:
        from_attributes = True


# Response Trả về danh sách User cho Admin (Đầy đủ thuộc tính)
class UserOut(BaseModel):
    id: int
    avatar: Optional[str] = None  # <-- Đã thêm thành công
    username: str
    email: str
    role: str
    is_active: bool = True
    is_banned: bool = False
    is_deleted: bool = False
    is_muted: bool = False
    is_premium: bool = False
    premium_expired_at: Optional[datetime] = None
    premium_lifetime: bool = False
    max_screens: int = 1
    video_quality: str = "1080p"
    ad_free: bool = False
    can_download: bool = False

    model_config = {
        "from_attributes": True
    }


# Request Gửi OTP quên mật khẩu
class ForgotPassword(BaseModel):
    email: EmailStr


# Request Xác nhận OTP & Đặt lại mật khẩu
class ResetPassword(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=6)
    password: str = Field(..., min_length=6)


class ChangePassword(BaseModel):
    email: Optional[EmailStr] = None  # Cho phép None để khi dùng Cookie đổi mật khẩu không bị bắt buộc truyền email
    old_password: str
    new_password: str


class SendOTPRequest(BaseModel):
    user_id: int
    current_password: str
    new_email: EmailStr


class VerifyOTPChangeEmailRequest(BaseModel):
    user_id: int
    new_email: EmailStr
    otp: str
    
class AvatarUpdate(BaseModel):
    avatar: str

class FullNameUpdate(BaseModel):
    full_name: str