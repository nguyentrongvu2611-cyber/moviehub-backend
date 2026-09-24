import os
import resend
from pydantic import EmailStr
from dotenv import load_dotenv

load_dotenv()

# Cấu hình Resend API Key
resend.api_key = os.getenv("RESEND_API_KEY")

async def send_otp_email(email_to: EmailStr, otp_code: str):
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #141414; color: #ffffff;">
        <div style="max-width: 500px; margin: 0 auto; background: #222222; padding: 20px; border-radius: 8px; border: 1px solid #333;">
            <h2 style="color: #e50914; text-align: center; margin-bottom: 20px;">MovieHub - Mã Xác Thực OTP</h2>
            <p style="color: #eee;">Chào bạn,</p>
            <p style="color: #ccc;">Bạn đang yêu cầu xác thực email trên hệ thống <b>MovieHub</b>.</p>
            <p style="color: #ccc;">Mã OTP xác thực của bạn là:</p>
            <div style="text-align: center; margin: 25px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #e50914; background: #141414; padding: 12px 24px; border-radius: 6px; border: 1px solid #e50914; display: inline-block;">
                    {otp_code}
                </span>
            </div>
            <p style="color: #888; font-size: 13px; text-align: center;">Mã này có hiệu lực trong 5 phút. Vui lòng không chia sẻ mã này cho ai.</p>
        </div>
    </div>
    """

    try:
        # Resend gửi qua HTTPS nên Render KHÔNG THỂ CHẶN
        params = {
            "from": "MovieHub <onboarding@resend.dev>",  # Domain mặc định của Resend
            "to": [email_to],
            "subject": "[MovieHub] Mã xác thực OTP",
            "html": html_content,
        }
        
        email = resend.Emails.send(params)
        print(f"✅ [Resend] Đã gửi email OTP thành công! ID: {email}")
    except Exception as e:
        print(f"❌ [Resend] Lỗi gửi mail chi tiết: {type(e).__name__} - {str(e)}")
        raise e