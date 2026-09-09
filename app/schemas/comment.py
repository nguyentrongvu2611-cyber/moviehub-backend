from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, description="Nội dung bình luận")
    rating: int = Field(..., ge=1, le=10, description="Đánh giá từ 1 đến 10 sao")

class CommentCreate(CommentBase):
    pass

class CommentResponse(CommentBase):
    id: int
    movie_id: int
    user_id: int
    username: Optional[str] = None
    avatar: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class MovieCommentsSummary(BaseModel):
    avg_rating: float = Field(..., description="Điểm đánh giá trung bình")
    total_ratings: int = Field(..., description="Tổng số lượt đánh giá")
    comments: List[CommentResponse]