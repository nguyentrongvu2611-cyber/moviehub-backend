import smtplib
from email.message import EmailMessage
from app.core.config import settings

def send_reset_otp_email(to_email: str, otp: str):
    msg = EmailMessage()
    msg['Subject'] = "Mã OTP đặt lại mật khẩu"
    msg['From'] = settings.MAIL_FROM
    msg['To'] = to_email
    msg.set_content(f"Mã OTP để đặt lại mật khẩu của bạn là: {otp}. Mã có hiệu lực trong 5 phút.")

    with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
        server.starttls()
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.send_message(msg)