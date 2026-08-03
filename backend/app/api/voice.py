from pathlib import Path
import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, VoiceGender
from app.schemas.voice import SynthesisRequest, TranscriptionResponse
from app.services.voice import (
    AudioTranscriptionError,
    SpeechSynthesisError,
    get_stt_service,
    get_tts_service,
)

router = APIRouter(prefix="/voice", tags=["voice"])
logger = logging.getLogger("uvicorn.error")

AUDIO_SUFFIX_BY_CONTENT_TYPE = {
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
    "audio/x-m4a": ".m4a",
    "audio/x-wav": ".wav",
    "video/webm": ".webm",
}
ALLOWED_AUDIO_SUFFIXES = {".m4a", ".mp3", ".ogg", ".wav", ".webm"}


async def _read_audio(audio: UploadFile) -> tuple[bytes, str]:
    content_type = (audio.content_type or "").split(";", maxsplit=1)[0].lower()
    suffix = Path(audio.filename or "").suffix.lower()
    if content_type in AUDIO_SUFFIX_BY_CONTENT_TYPE:
        audio_suffix = AUDIO_SUFFIX_BY_CONTENT_TYPE[content_type]
    elif (
        content_type == "application/octet-stream" and suffix in ALLOWED_AUDIO_SUFFIXES
    ):
        audio_suffix = suffix
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload WebM, Ogg, MP4/M4A, MP3, or WAV audio.",
        )

    audio_bytes = await audio.read(settings.max_audio_upload_bytes + 1)
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded audio is empty.",
        )
    if len(audio_bytes) > settings.max_audio_upload_bytes:
        limit_mb = settings.max_audio_upload_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio must be at most {limit_mb} MB.",
        )
    return audio_bytes, audio_suffix


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
) -> TranscriptionResponse:
    logger.info(
        "Voice upload accepted: field=audio filename=%s content_type=%s",
        audio.filename,
        audio.content_type,
    )
    audio_bytes, suffix = await _read_audio(audio)
    try:
        result = await get_stt_service().transcribe(
            audio_bytes,
            suffix=suffix,
        )
    except AudioTranscriptionError as exc:
        logger.warning(
            "Voice upload passed multipart validation but transcription failed: "
            "detail=%s",
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return TranscriptionResponse(
        text=result.text,
        detected_language=result.language,
        language_confidence=result.language_probability,
    )


@router.post(
    "/synthesize",
    response_class=Response,
    responses={200: {"content": {"audio/mpeg": {}}}},
)
async def synthesize_speech(
    payload: SynthesisRequest,
    db: AsyncSession = Depends(get_db),
) -> Response:
    if len(payload.text) > settings.tts_max_text_characters:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Text must be at most {settings.tts_max_text_characters} characters."
            ),
        )

    voice_gender = VoiceGender.MALE
    if payload.user_id is not None:
        user = await db.get(User, payload.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        voice_gender = user.preferred_voice_gender

    tts_service = get_tts_service()
    try:
        audio = await tts_service.synthesize(
            payload.text,
            language=payload.language,
            gender=voice_gender,
        )
    except SpeechSynthesisError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="virtualpresence-reply.mp3"',
            "X-Voice": tts_service.voice_for_language(
                payload.language,
                voice_gender,
            ),
        },
    )
