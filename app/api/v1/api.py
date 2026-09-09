from fastapi import APIRouter
from app.api.v1.endpoints import (
    admin,
    auth,
    category,
    history,
    movies,  # Sửa 'movie' thành 'movies'
    payment,
    streaming,
    upload,
    watchlist
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(category.router, prefix="/categories", tags=["Categories"])
api_router.include_router(movies.router, prefix="/movies", tags=["Movies"]) # Dùng movies.router
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
api_router.include_router(history.router, prefix="/history", tags=["History"])
api_router.include_router(streaming.router, prefix="/streaming", tags=["Streaming"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["Watchlist"])
api_router.include_router(payment.router, prefix="/payments", tags=["payments"])