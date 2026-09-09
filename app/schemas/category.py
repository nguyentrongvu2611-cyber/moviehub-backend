from pydantic import BaseModel, Field

# Base schema chứa các field chung
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Tên thể loại phim")

# Schema dùng khi Request tạo mới/cập nhật category
class CategoryCreate(CategoryBase):
    pass

# Schema dùng khi Response trả dữ liệu ra API
class CategoryResponse(CategoryBase):
    id: int

    model_config = {
        "from_attributes": True
    }