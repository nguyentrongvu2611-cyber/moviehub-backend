import os
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

# Cấu hình lấy từ file .env của bạn
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", os.getenv("MAIL_USERNAME")),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_otp_email(email_to: EmailStr, otp_code: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 500px; margin: 0 auto; background: #ffffff; padding: 20px; border-radius: 8px;">
            <h2 style="color: #5835ff; text-align: center;">MovieHub - Mã Xác Thực OTP</h2>
            <p>Chào bạn,</p>
            <p>Bạn đang yêu cầu thay đổi địa chỉ email trên hệ thống <b>MovieHub</b>.</p>
            <p>Mã OTP xác thực của bạn là:</p>
            <div style="text-align: center; margin: 20px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #5835ff; background: #f0edff; padding: 10px 20px; border-radius: 6px;">
                    {otp_code}
                </span>
            </div>
            <p style="color: #666; font-size: 13px;">Mã này có hiệu lực trong 5 phút. Vui lòng không chia sẻ mã này với bất kỳ ai.</p>
        </div>
    </div>
    """

    message = MessageSchema(
        subject="[MovieHub] Mã xác thực đổi địa chỉ Email",
        recipients=[email_to],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message)