# VirtualPresence

VirtualPresence is an AI-native virtual assistant platform. Phase 4 combines
local face enrollment, identification, expression classification, and
short-burst anti-spoofing with personalized Anthropic-powered text and voice
conversation. FastAPI persists identities, recognition context, interaction
sessions, and messages in PostgreSQL, while React provides webcam, chat,
microphone recording, and spoken-response interfaces for end-to-end testing.

This phase intentionally does **not** implement avatar rendering or lip-sync.

## Stack

- Backend: FastAPI, async SQLAlchemy 2.0, asyncpg, Alembic, PostgreSQL
- Jobs: Celery with Memurai (Redis-compatible on Windows)
- Face pipeline: OpenCV YuNet + SFace, FER+ emotion ONNX, active liveness challenge
- Conversation: Anthropic Python SDK, automatic language detection, local mock mode
- Voice: local faster-whisper STT and multilingual Microsoft Edge TTS
- Frontend: React 19, Vite, Tailwind CSS, TanStack Query, TypeScript

## Repository layout

```text
VirtualPresence/
├── backend/
│   ├── alembic/                 # env.py, script template, revisions
│   ├── app/
│   │   ├── api/                 # HTTP routes
│   │   ├── core/                # settings and async database session
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # API schemas
│   │   └── services/
│   │       ├── conversation/    # Language detection, chat, and Anthropic client
│   │       ├── face/            # Recognition, emotion, and liveness
│   │       └── voice/           # Local transcription and speech synthesis
│   ├── scripts/
│   └── tests/
└── frontend/
    └── src/
        ├── api/
        ├── components/
        ├── hooks/
        └── pages/
```

## Face model choices on Windows

The project uses `opencv-contrib-python-headless` instead of the Python
`face_recognition` package. `face_recognition` depends on `dlib`; on Windows,
`dlib` frequently requires a compatible C++ build toolchain and CMake, making a
clean `pip` install unreliable. OpenCV publishes Windows wheels for Python 3.11,
and its DNN APIs load the YuNet and SFace ONNX models directly.

Emotion detection uses the lightweight FER+ ONNX model through the same OpenCV
DNN module. This avoids adding DeepFace and its much larger TensorFlow dependency
tree. FER+ accepts 64×64 grayscale face crops and returns eight model classes;
the service maps these into the seven public labels requested by VirtualPresence,
folding `contempt` into `neutral`.

The setup script downloads these upstream ONNX models:

- `face_detection_yunet_2023mar.onnx`
- `face_recognition_sface_2021dec.onnx`
- `emotion-ferplus-8.onnx` from a GitHub release mirror of the ONNX Model Zoo artifact

SFace returns a cosine similarity. The default match threshold is `0.363`, the
same cosine threshold documented in OpenCV's
[DNN face tutorial](https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html).
The threshold can be changed through `FACE_MATCH_THRESHOLD`.

### Liveness limitations

The liveness service requires five frames and asks the user to turn their head
gently. Normalized YuNet landmarks measure facial-geometry changes while
affine-aligned crops measure non-rigid residual motion. A rigidly moved print or
screen therefore cannot pass merely by producing pixel differences.

Single-frame cues—moire peaks, opponent-channel noise, edge sharpness, color
distribution, and broad specular glare—remain secondary. They contribute at
most 15% of the final result and cannot establish liveness alone. The default
`LIVENESS_THRESHOLD` is `0.70`; a valid result also requires five detected
frames and a head-turn challenge score of at least `0.55`. Blink detection is
only a supporting signal because eye cascades can be unstable under pose change.

This is intentionally a practical heuristic, not biometric proof of presence.
A replay synchronized to the challenge or sophisticated rendering can still
bypass it, while difficult lighting or a low-quality webcam can cause false
rejections. The color cue can also vary with lighting, camera processing, and
skin tone, which is why it has low weight. High-risk production authentication
should use a trained, independently benchmarked PAD model or depth/IR hardware.

If you specifically need `face_recognition`, use one of these Windows options:

1. Install Miniconda, open an Anaconda PowerShell prompt, and run
   `conda install -c conda-forge dlib face_recognition`.
2. Install a prebuilt `dlib` wheel that exactly matches the Python version and
   architecture, then run `pip install face_recognition`.

Those alternatives are documented only; the working implementation in this
repository is OpenCV-based and requires no `dlib`.

## Windows prerequisites

Install:

- Python 3.11 (64-bit)
- Node.js 20.19 or newer
- PostgreSQL; set the `postgres` user password to `rodolfo`
- [Memurai Developer](https://www.memurai.com/get-memurai) on its default port
  `6379`

Check the database and cache services in PowerShell:

```powershell
psql --version
Get-Service postgresql*
Get-Service Memurai
Start-Service Memurai
```

Memurai speaks the Redis protocol, so Celery uses
`redis://localhost:6379/0` without a Memurai-specific Python package.

## One-command setup

Open PowerShell in the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\backend\scripts\setup_windows.ps1
```

The script performs the exact local setup:

1. Creates `backend\.venv`.
2. Installs the pinned Python packages, including the OpenCV Windows wheel.
3. Downloads the three ONNX model files used by recognition and emotion analysis.
4. Creates PostgreSQL database `virtualpresence` if missing.
5. Runs `alembic upgrade head`.
6. Installs frontend packages.

The multilingual faster-whisper `base` model downloads automatically on the
first transcription request and is cached for subsequent runs.

The local `.env` files are already configured for development. Copy the example
files if they are absent:

```powershell
Copy-Item .\backend\.env.example .\backend\.env
Copy-Item .\frontend\.env.example .\frontend\.env
```

## Manual setup

Every command below is PowerShell-compatible and deliberately avoids shell
`&&` chaining.

### Backend

```powershell
Set-Location .\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python .\scripts\download_face_models.py
```

Create the database and apply the migration:

```powershell
$env:PGPASSWORD = "rodolfo"
createdb -U postgres -h localhost virtualpresence
python -m alembic upgrade head
python -m alembic current
```

The `alembic/versions/` directory is created manually and committed.
`alembic/script.py.mako` is also committed, so future autogeneration works:

```powershell
python -m alembic revision --autogenerate -m "describe change"
python -m alembic upgrade head
```

Start the API:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

API docs are available at <http://localhost:8000/docs>.

### Celery with Memurai

Open another PowerShell window:

```powershell
Set-Location .\backend
.\.venv\Scripts\Activate.ps1
celery -A app.services.celery_app:celery_app worker --loglevel=info --pool=solo
```

`--pool=solo` is intentional for dependable local Celery operation on Windows.
The example task is `virtualpresence.health_check`.

### Frontend

Open a third PowerShell window:

```powershell
Set-Location .\frontend
npm.cmd install
npm.cmd run dev
```

Visit <http://localhost:5173>, allow camera access, then:

1. Select **Enroll**, enter a name, center exactly one face, and capture.
2. Select **Identify** and capture another frame.
3. Review the identity, emotion, and liveness badges.
4. After a successful live match, use the unlocked chat panel. Type a message
   or tap the microphone, speak, and tap stop.
5. The assistant reply is spoken automatically unless the speaker button is
   muted. Messages and transcripts are restored from PostgreSQL.

Camera access works on `localhost`. A non-local production site must be served
over HTTPS for `getUserMedia`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/face/enroll` | Multipart `image`, `name`, optional `email`, optional `preferred_language` |
| `POST` | `/face/identify` | Multipart `image` plus optional repeated `frames`; returns identity, emotion, and liveness |
| `GET` | `/face/users` | Lists enrolled users |
| `POST` | `/conversation/message` | JSON `{ "user_id", "message" }`; returns the assistant reply and detected input language |
| `GET` | `/conversation/users/{user_id}/history` | Full persisted message history for a recently verified user |
| `GET` | `/conversation/users/{user_id}/history?current_session_only=true` | Messages from only the active conversation session |
| `DELETE` | `/conversation/users/{user_id}/history` | Ends the active session without deleting persisted messages |
| `GET` | `/memory/users/{user_id}/facts` | Lists the durable personal facts remembered for a user |
| `DELETE` | `/memory/users/{user_id}/facts/{fact_id}` | Permanently removes one remembered fact |
| `GET` | `/analytics/overview` | Summary usage, recognition, session, and memory metrics |
| `GET` | `/analytics/recognition-trends?days=30` | Daily confidence, liveness, and spoof-detection trends |
| `GET` | `/analytics/emotion-distribution` | Aggregate recognition emotion distribution |
| `GET` | `/analytics/usage-patterns` | Daily and hourly session/message activity in UTC |
| `PATCH` | `/users/{user_id}/settings` | Updates user settings such as `{ "preferred_voice_gender": "female" }` |
| `POST` | `/voice/transcribe` | Multipart `audio`; returns transcript, detected language, and language confidence |
| `POST` | `/voice/synthesize` | JSON `{ "text", "language", "user_id" }` (`user_id` optional); returns inline MP3 audio using the user's preferred voice or the male default |
| `GET` | `/health` | API health check |

PowerShell example with an existing image:

```powershell
$EnrollForm = @{
    image = Get-Item "C:\path\to\clear-face-photo.jpg"
    name = "Ada Lovelace"
    email = "ada@example.com"
    preferred_language = "en"
}
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/face/enroll" -Form $EnrollForm

$IdentifyForm = @{
    image = Get-Item "C:\path\to\second-face-photo.jpg"
}
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/face/identify" -Form $IdentifyForm
```

Every valid identification attempt is written to `recognition_events`, including
no-face, unmatched, and suspected spoof results. Stored analysis includes
`detected_emotion`, `emotion_confidence`, `is_live`, and
`liveness_confidence`. When liveness fails, the API returns
`outcome: "spoof_detected"` and may still include the candidate user, but the
frontend clearly labels that identity as unverified.

Conversation messages are also checked for durable facts such as ongoing
projects, preferences, goals, and stable profile details. Relevant facts are
included as untrusted context for later replies and can be reviewed or deleted
through the memory API. Short-lived states such as being tired or upset are not
stored. New users default to a male synthesized voice; `male` and `female`
preferences can be selected through the user settings endpoint.

## Anthropic conversation setup

Conversation mock mode is enabled by default, so the complete API and frontend
flow works without credits or an API key. The mock produces deterministic,
identity-, emotion-, and language-aware template replies:

```dotenv
LLM_MOCK_MODE=true
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6
```

To use the live Anthropic API, edit `backend\.env`:

```dotenv
LLM_MOCK_MODE=false
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-sonnet-4-6
```

Restart Uvicorn after changing the environment. The implementation uses the
official [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
and its async messages client. The user's input language is detected locally;
the model is instructed to answer entirely in that language and to adapt its
tone gently to the latest emotion signal without presenting it as a diagnosis.

As a basic access guard, conversation routes require a successful live
recognition event for that user within the previous 300 seconds. Change
`CONVERSATION_RECOGNITION_TTL_SECONDS` in `backend\.env` if needed. A new
recognition begins a new interaction session; subsequent messages in that visit
reuse recent history, and the history endpoint returns messages across all
sessions. This time-window check is not a replacement for authenticated
application sessions in a production deployment.

PowerShell example after the frontend or `/face/identify` has produced a recent
verified recognition:

```powershell
$MessageBody = @{
    user_id = "recognized-user-uuid"
    message = "Hello, can you help me plan my day?"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8000/conversation/message" `
    -ContentType "application/json" `
    -Body $MessageBody
```

Voice-originated conversation messages use the same endpoint with
`audio_transcript_of` instead of `message`. Exactly one input field is required:

```powershell
$VoiceMessageBody = @{
    user_id = "recognized-user-uuid"
    audio_transcript_of = "Hello, this was transcribed from my recording."
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8000/conversation/message" `
    -ContentType "application/json" `
    -Body $VoiceMessageBody
```

## Voice setup on Windows

Speech-to-text uses
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) with the multilingual
`base` model on CPU using `int8` quantization. Its PyAV dependency bundles the
required FFmpeg libraries, so no separate FFmpeg executable is needed. The first
transcription needs internet access to download the model; transcription is
local after the model is cached. Windows may warn that the Hugging Face cache
cannot use symlinks unless Developer Mode is enabled; the fallback cache still
works and does not require administrator privileges, but can use more disk space.

The defaults are suitable for a typical Windows development machine:

```dotenv
STT_MODEL_SIZE=base
STT_DEVICE=cpu
STT_COMPUTE_TYPE=int8
STT_BEAM_SIZE=3
MAX_AUDIO_UPLOAD_BYTES=26214400
```

For a CUDA installation, follow faster-whisper's current CUDA 12 and cuDNN
requirements before setting `STT_DEVICE=cuda` and an appropriate compute type.
The CPU configuration is the supported default and requires no NVIDIA software.

Text-to-speech uses
[edge-tts](https://github.com/rany2/edge-tts), selecting Mandarin
`zh-CN-XiaoxiaoNeural` for `zh`, English `en-US-AriaNeural` for `en`, and
matching voices for the other languages supported by the conversation layer.
It needs internet access because it calls Microsoft's online Edge speech
service, but it needs no API key.

```dotenv
TTS_DEFAULT_VOICE=en-US-AriaNeural
TTS_MANDARIN_VOICE=zh-CN-XiaoxiaoNeural
TTS_MAX_TEXT_CHARACTERS=5000
```

The transcription endpoint accepts WebM/Opus, Ogg, MP4/M4A, MP3, and WAV.
Browser recording works on `localhost`; deployed sites require HTTPS for
microphone access. Autoplay is attempted after each user-initiated exchange,
but restrictive browser policies can still require a further click.

PowerShell API examples:

```powershell
$AudioForm = @{
    audio = Get-Item "C:\path\to\recording.webm"
}
Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8000/voice/transcribe" `
    -Form $AudioForm

$SpeechBody = @{
    text = "很高兴再次见到你。"
    language = "zh"
} | ConvertTo-Json
Invoke-WebRequest `
    -Method Post `
    -Uri "http://localhost:8000/voice/synthesize" `
    -ContentType "application/json" `
    -Body $SpeechBody `
    -OutFile ".\virtualpresence-reply.mp3"
```

## Liveness calibration

The comparison script captures the exact attack described above and reports
every component score. Close other camera applications, then run:

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe .\scripts\compare_liveness.py --camera 0
```

First present your genuine face and turn your head gently during capture. The
script then pauses so you can hold up the printed/screen photo and move it in the
same way. Calibration passes only when the genuine burst is live and at least
`0.70`, while the held-photo burst is not live and below `0.50`.

You can also compare previously captured folders containing at least five
chronologically named images each:

```powershell
.\.venv\Scripts\python.exe .\scripts\compare_liveness.py `
    --live .\calibration\live `
    --spoof .\calibration\spoof
```

Treat those targets as a local acceptance check, not a universal accuracy
claim. Proper PAD evaluation requires real and attack videos across multiple
people, devices, printers, displays, and lighting conditions.

## Verification

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m alembic check

Set-Location ..\frontend
npm.cmd run lint
npm.cmd run build
```
