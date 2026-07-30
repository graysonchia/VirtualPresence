from fastapi import APIRouter

from app.api.face import router as face_router


api_router = APIRouter()
api_router.include_router(face_router)

