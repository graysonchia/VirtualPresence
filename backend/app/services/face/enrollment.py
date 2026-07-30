import asyncio
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.face_embedding import FaceEmbedding
from app.models.user import User
from app.services.face.engine import OpenCVFaceEngine


async def enroll_user(
    db: AsyncSession,
    engine: OpenCVFaceEngine,
    *,
    image_bytes: bytes,
    image_suffix: str,
    name: str,
    email: str,
    preferred_language: str,
) -> tuple[User, FaceEmbedding]:
    embedding_vector = (
        await asyncio.to_thread(
            engine.extract_embeddings,
            image_bytes,
            require_single_face=True,
        )
    )[0]

    user = User(
        id=str(uuid4()),
        name=name.strip(),
        email=email.strip().lower(),
        preferred_language=preferred_language.strip().lower(),
    )
    storage_dir = settings.enrollment_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    safe_suffix = (
        image_suffix.lower()
        if image_suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        else ".jpg"
    )
    image_path = storage_dir / f"{user.id}{safe_suffix}"
    relative_path = image_path.relative_to(settings.enrollment_storage_dir.parent.parent)

    face_embedding = FaceEmbedding(
        id=str(uuid4()),
        user_id=user.id,
        embedding_vector=embedding_vector,
        sample_image_path=str(relative_path).replace("\\", "/"),
    )

    image_path.write_bytes(image_bytes)
    try:
        db.add_all([user, face_embedding])
        await db.commit()
        await db.refresh(user)
        await db.refresh(face_embedding)
    except Exception:
        await db.rollback()
        _remove_failed_sample(image_path)
        raise

    return user, face_embedding


def _remove_failed_sample(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        # A failed cleanup must not hide the original database error.
        pass
