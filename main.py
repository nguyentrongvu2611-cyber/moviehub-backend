import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="MovieHub API",
    version="1.0.0"
)

os.makedirs("uploads/posters", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    return {
        "message": "MovieHub Backend đang hoạt động"
    }