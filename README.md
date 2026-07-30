# VirtualPresence

VirtualPresence is an AI-native virtual assistant platform. Phase 2 implements
local face enrollment, identification, expression classification, and
spatial/short-burst anti-spoofing signals. A FastAPI API stores SFace embeddings and
recognition results in PostgreSQL, while a React page captures webcam frames for
end-to-end testing.

This phase intentionally does **not** implement avatars, an LLM, or
conversations. The conversation tables exist for the agreed data foundation,
but no conversation endpoints are exposed.

## Stack

- Backend: FastAPI, async SQLAlchemy 2.0, asyncpg, Alembic, PostgreSQL
- Jobs: Celery with Memurai (Redis-compatible on Windows)
- Face pipeline: OpenCV YuNet + SFace, FER+ emotion ONNX, active liveness challenge
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
│   │       └── face/            # Recognition, emotion, and liveness
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

Camera access works on `localhost`. A non-local production site must be served
over HTTPS for `getUserMedia`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/face/enroll` | Multipart `image`, `name`, optional `email`, optional `preferred_language` |
| `POST` | `/face/identify` | Multipart `image` plus optional repeated `frames`; returns identity, emotion, and liveness |
| `GET` | `/face/users` | Lists enrolled users |
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
