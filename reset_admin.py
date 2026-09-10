import bcrypt
from app.core.database import SessionLocal

# Import trực tiếp tất cả các model để SQLAlchemy đăng ký đủ mapper
from app.models.user import User
from app.models.movie import Movie
from app.models.comment import Comment  # Import bắt buộc để giải quyết lỗi
try:
    from app.models.rating import Rating
except ImportError:
    pass

db = SessionLocal()

try:
    new_password = "123456"
    hashed_pwd = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Tìm tài khoản admin
    admin_user = db.query(User).filter((User.username == "admin") | (User.email == "admin@gmail.com")).first()

    if admin_user:
        admin_user.password = hashed_pwd
        admin_user.is_active = True
        db.commit()
        print("--> Đã cập nhật mật khẩu tài khoản admin thành công! Mật khẩu mới: 123456")
    else:
        new_admin = User(
            username="admin",
            email="admin@gmail.com",
            password=hashed_pwd,
            role="admin",
            is_active=True,
            is_premium=True
        )
        db.add(new_admin)
        db.commit()
        print("--> Đã tạo mới tài khoản admin thành công! Username: admin | Mật khẩu: 123456")

except Exception as e:
    print(f"Lỗi: {e}")
    db.rollback()
finally:
    db.close()