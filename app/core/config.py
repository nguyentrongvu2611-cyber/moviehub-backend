import os
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr
from dotenv import load_dotenv

load_dotenv()

mail_port = int(os.getenv("MAIL_PORT", 465))

# Tự động điều chỉnh SSL/STARTTLS theo cổng 465 hoặc 587
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", os.getenv("MAIL_USERNAME")),
    MAIL_PORT=mail_port,
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_FROM_NAME="MovieHub",
    MAIL_STARTTLS=(mail_port == 587),  # True nếu port 587
    MAIL_SSL_TLS=(mail_port == 465),   # True nếu port 465
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_otp_email(email_to: EmailStr, otp_code: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #141414; color: #ffffff;">
        <div style="max-width: 500px; margin: 0 auto; background: #222222; padding: 20px; border-radius: 8px; border: 1px solid #333;">
            <h2 style="color: #e50914; text-align: center; margin-bottom: 20px;">MovieHub - Mã Xác Thực OTP</h2>
            <p style="color: #eee;">Chào bạn,</p>
            <p style="color: #ccc;">Bạn đang yêu cầu thay đổi địa chỉ email trên hệ thống <b>MovieHub</b>.</p>
            <p style="color: #ccc;">Mã OTP xác thực của bạn là:</p>
            <div style="text-align: center; margin: 25px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #e50914; background: #141414; padding: 12px 24px; border-radius: 6px; border: 1px solid #e50914; display: inline-block;">
                    {otp_code}
                </span>
            </div>
            <p style="color: #888; font-size: 13px; text-align: center;">Mã này có hiệu lực trong 5 phút. Vui lòng không chia sẻ mã này với bất kỳ ai.</p>
        </div>
    </div>
    """

    message = MessageSchema(
        subject="[MovieHub] Mã xác thực đổi địa chỉ Email",
        recipients=[email_to],
        body=html,
        subtype=MessageType.html
    )

    try:
        fm = FastMail(conf)
        await fm.send_message(message)
        print(f"✅ Đã gửi email OTP thành công tới: {email_to}")
    except Exception as e:
        print(f"❌ LỖI FASTMAIL CHI TIẾT: {type(e).__name__} - {str(e)}")
        raise e