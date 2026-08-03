from fastapi import APIRouter

from app.api.conversation import router as conversation_router
from app.api.face import router as face_router
from app.api.memory import router as memory_router
from app.api.users import router as users_router
from app.api.voice import router as voice_router


api_router = APIRouter()
api_router.include_router(face_router)
api_router.include_router(conversation_router)
api_router.include_router(memory_router)
api_router.include_router(users_router)
api_router.include_router(voice_router)
