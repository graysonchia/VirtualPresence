"""API for the single-machine edge inference architecture demonstration."""

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.face import _read_image
from app.core.database import get_db
from app.core.exceptions import FaceModelsMissingError
from app.schemas.face import (
    EdgeArchitectureSummary,
    EdgeBenchmarkResponse,
    IdentificationResponse,
)
from app.services.face.edge_inference import (
    benchmark_edge_inference,
    get_edge_face_engine,
)
from app.services.face.emotion import get_emotion_detector
from app.services.face.liveness import get_liveness_detector
from app.services.face.recognition import identify_user


router = APIRouter(prefix="/edge-face", tags=["edge face"])


@router.get("/benchmark", response_model=EdgeBenchmarkResponse)
async def benchmark() -> EdgeBenchmarkResponse:
    try:
        result = await asyncio.to_thread(benchmark_edge_inference)
    except (FaceModelsMissingError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return EdgeBenchmarkResponse.model_validate(result, from_attributes=True)


@router.post("/identify-edge", response_model=IdentificationResponse)
async def identify_edge(
    image: UploadFile = File(...),
    frames: list[UploadFile] | None = File(default=None),
    db: AsyncSession = Depends(get_db),
) -> IdentificationResponse:
    """Identify locally with bounded YuNet input and INT8 SFace embeddings."""

    image_bytes = await _read_image(image)
    frame_uploads = frames or []
    if len(frame_uploads) > 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Send at most four additional liveness frames.",
        )
    additional_frame_bytes = [
        await _read_image(frame) for frame in frame_uploads if frame.filename
    ]
    try:
        result = await identify_user(
            db,
            get_edge_face_engine(),
            get_emotion_detector(),
            get_liveness_detector(),
            image_bytes=image_bytes,
            additional_frame_bytes=additional_frame_bytes,
        )
    except FaceModelsMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
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


@router.get("/architecture-summary", response_model=EdgeArchitectureSummary)
async def architecture_summary() -> EdgeArchitectureSummary:
    return EdgeArchitectureSummary(
        concept="Privacy-by-design edge inference for sensitive biometric data",
        deployment_scope=(
            "Single-machine demonstration only: the standard and edge-optimized "
            "paths run in this API process, not on a separate physical edge device."
        ),
        architecture_pattern=[
            "Capture a short frame burst at the camera or kiosk.",
            "Run bounded-resolution YuNet detection and INT8 SFace embedding locally.",
            "Run liveness and emotion analysis inside the same trusted device boundary.",
            "Transmit only a lightweight embedding or recognition result when a remote service is required.",
        ],
        privacy_boundary=[
            "Raw face frames do not need to leave the local device in a real deployment.",
            "Embeddings remain sensitive biometric identifiers and still require encryption, access controls, retention limits, and consent.",
            "This demo currently stores enrollment images locally for project functionality; production edge deployments should minimize or eliminate that retention.",
        ],
        performance_tradeoffs=[
            "INT8 SFace reduces runtime parameter footprint and can reduce CPU latency.",
            "YuNet input is capped at 320 pixels on its longest side, reducing work but potentially missing small or distant faces.",
            "Quantization can shift embedding similarity, so the benchmark reports cosine fidelity and the edge endpoint exposes real matching tradeoffs.",
            "Results vary by CPU, OpenCV build, frame dimensions, and enrolled samples.",
        ],
        limitations=[
            "No separate camera, mobile SoC, edge accelerator, network hop, power measurement, or hardware isolation is simulated.",
            "OpenCV quantizes SFace in memory and does not emit a deployable INT8 ONNX artifact from this path.",
            "Benchmark accuracy is embedding agreement with FP32, not demographic or population-level recognition accuracy.",
        ],
        project_status=(
            "Final architectural concept complete: face recognition, liveness, emotion, multilingual LLM conversation, "
            "3D avatar emotion sync, personal memory/RAG, analytics, and edge inference are represented. "
            "Voice STT/TTS remains a known, deliberately deprioritized gap."
        ),
    )
