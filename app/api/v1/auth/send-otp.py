import random
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.models.user import User  
from app.core.database import get_db
from app.core.config import send_otp_email 

router = APIRouter()

class SendOTPRequest(BaseModel):
    user_id: int
    current_password: str
    new_email: EmailStr

@router.post("/send-otp")
async def send_otp_for_email_change(data: SendOTPRequest, db: Session = Depends(get_db)):
    # 1. Kiểm tra User có tồn tại không
    current_user = db.query(User).filter(User.id == data.user_id).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Người dùng không tồn tại!"
        )

    # 2. Kiểm tra email mới có trùng email hiện tại không
    if current_user.email == data.new_email.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email mới phải khác email hiện tại!"
        )

    # 3. Kiểm tra email mới đã bị tài khoản khác sử dụng chưa
    existing_user = db.query(User).filter(User.email == data.new_email.strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email này đã được sử dụng bởi một tài khoản khác!"
        )

    # 4. (Tùy chọn) Kiểm tra mật khẩu hiện tại...
    # if not verify_password(data.current_password, current_user.password):
    #     raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng!")

    # 5. Tạo mã OTP ngẫu nhiên 6 chữ số
    otp_code = str(random.randint(100000, 999999))

    # 6. Lưu OTP vào DB hoặc Redis/Cache để đối chiếu khi user nhập (Tùy logic dự án)
    # current_user.otp_code = otp_code
    # db.commit()

    # 7. Gửi Email chứa mã OTP
    try:
        await send_otp_email(data.new_email.strip(), otp_code)
    except Exception as e:
        print("Lỗi gửi Mail:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi kết nối tới máy chủ gửi mail, vui lòng thử lại sau!"
        )

    return {"message": f"Đã gửi mã OTP thành công tới {data.new_email}"}