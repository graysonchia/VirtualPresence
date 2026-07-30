import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    FaceModelsMissingError,
    FaceNotFoundError,
    MultipleFacesError,
)
from app.models.user import User
from app.schemas.face import (
    EnrollmentResponse,
    IdentificationResponse,
    UserListResponse,
)
from app.services.face.engine import get_face_engine
from app.services.face.emotion import get_emotion_detector
from app.services.face.enrollment import enroll_user
from app.services.face.liveness import get_liveness_detector
from app.services.face.recognition import identify_user


router = APIRouter(prefix="/face", tags=["face"])
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


async def _read_image(image: UploadFile) -> bytes:
    suffix = Path(image.filename or "").suffix.lower()
    is_powershell_file_upload = (
        image.content_type == "application/octet-stream"
        and suffix in ALLOWED_IMAGE_SUFFIXES
    )
    if image.content_type not in ALLOWED_CONTENT_TYPES and not is_powershell_file_upload:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG, or WebP image.",
        )
    image_bytes = await image.read(settings.max_upload_bytes + 1)
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image is empty.",
        )
    if len(image_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Images must be at most {settings.max_upload_bytes // (1024 * 1024)} MB.",
        )
    return image_bytes


def _generated_email(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".") or "user"
    return f"{slug}.{str(uuid4())[:8]}@virtualpresence.local"


@router.post(
    "/enroll",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def enroll(
    image: UploadFile = File(...),
    name: str = Form(..., min_length=1, max_length=120),
    email: str | None = Form(default=None, max_length=320),
    preferred_language: str = Form(default="en", min_length=2, max_length=10),
    db: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    image_bytes = await _read_image(image)
    normalized_email = email.strip() if email and email.strip() else _generated_email(name)

    try:
        engine = get_face_engine()
        user, embedding = await enroll_user(
            db,
            engine,
            image_bytes=image_bytes,
            image_suffix=Path(image.filename or "").suffix,
            name=name,
            email=normalized_email,
            preferred_language=preferred_language,
        )
    except FaceModelsMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (FaceNotFoundError, MultipleFacesError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email is already enrolled.",
        ) from exc

    return EnrollmentResponse(
        message=f"{user.name} enrolled successfully.",
        user=user,
        embedding_id=embedding.id,
    )


@router.post("/identify", response_model=IdentificationResponse)
async def identify(
    image: UploadFile = File(...),
    frames: list[UploadFile] | None = File(default=None),
    db: AsyncSession = Depends(get_db),
) -> IdentificationResponse:
    image_bytes = await _read_image(image)
    frame_uploads = frames or []
    if len(frame_uploads) > 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Send at most four additional liveness frames.",
        )
    additional_frame_bytes = [
        await _read_image(frame)
        for frame in frame_uploads
        if frame.filename
    ]
    try:
        engine = get_face_engine()
        emotion_detector = get_emotion_detector()
        liveness_detector = get_liveness_detector()
        result = await identify_user(
            db,
            engine,
            emotion_detector,
            liveness_detector,
            image_bytes=image_bytes,
            additional_frame_bytes=additional_frame_bytes,
        )
    except FaceModelsMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return IdentificationResponse(
        outcome=result.outcome,
        confidence=result.confidence,
        user=result.user,
        faces_detected=result.faces_detected,
        detected_emotion=result.detected_emotion,
        emotion_confidence=result.emotion_confidence,
        emotion_scores=result.emotion_scores,
        is_live=result.is_live,
        liveness_confidence=result.liveness_confidence,
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    result = await db.execute(select(User).order_by(User.enrolled_at.desc()))
    users = list(result.scalars().all())
    return UserListResponse(users=users, count=len(users))
