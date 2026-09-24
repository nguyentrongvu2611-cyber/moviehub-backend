import os
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr
from dotenv import load_dotenv

load_dotenv()

# Ép cổng 465 SSL chuẩn cho Render Cloud
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", os.getenv("MAIL_USERNAME")),
    MAIL_PORT=465,                     # Ép cứng port 465
    MAIL_SERVER="smtp.gmail.com",
    MAIL_FROM_NAME="MovieHub",
    MAIL_STARTTLS=False,               # Tắt STARTTLS
    MAIL_SSL_TLS=True,                 # Bật SSL/TLS
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_otp_email(email_to: EmailStr, otp_code: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #141414; color: #ffffff;">
        <div style="max-width: 500px; margin: 0 auto; background: #222222; padding: 20px; border-radius: 8px; border: 1px solid #333;">
            <h2 style="color: #e50914; text-align: center; margin-bottom: 20px;">MovieHub - Mã Xác Thực OTP</h2>
            <p style="color: #eee;">Chào bạn,</p>
            <p style="color: #ccc;">Bạn đang yêu cầu xác thực email trên <b>MovieHub</b>.</p>
            <p style="color: #ccc;">Mã OTP của bạn là:</p>
            <div style="text-align: center; margin: 25px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #e50914; background: #141414; padding: 12px 24px; border-radius: 6px; border: 1px solid #e50914; display: inline-block;">
                    {otp_code}
                </span>
            </div>
            <p style="color: #888; font-size: 13px; text-align: center;">Mã này có hiệu lực trong 5 phút.</p>
        </div>
    </div>
    """

    message = MessageSchema(
        subject="[MovieHub] Mã xác thực OTP",
        recipients=[email_to],
        body=html,
        subtype=MessageType.html
    )

    try:
        fm = FastMail(conf)
        await fm.send_message(message)
        print(f"✅ [Render] Đã gửi email OTP thành công tới: {email_to}")
    except Exception as e:
        print(f"❌ [Render] Lỗi gửi mail chi tiết: {type(e).__name__} - {str(e)}")
        raise e