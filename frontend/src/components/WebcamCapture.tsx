import {
  Camera,
  CameraOff,
  MoveHorizontal,
  RefreshCw,
  ScanFace,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

interface WebcamCaptureProps {
  busy?: boolean;
  captureBurst?: boolean;
  actionLabel: string;
  onCapture: (image: Blob, additionalFrames: Blob[]) => void;
}

export function WebcamCapture({
  busy = false,
  captureBurst = false,
  actionLabel,
  onCapture,
}: WebcamCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [capturing, setCapturing] = useState(false);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setReady(false);
  }, []);

  const startCamera = useCallback(async () => {
    stopCamera();
    setCameraError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setReady(true);
      }
    } catch {
      setCameraError(
        "Camera access was blocked. Allow camera permission and try again.",
      );
    }
  }, [stopCamera]);

  useEffect(() => {
    void startCamera();
    return stopCamera;
  }, [startCamera, stopCamera]);

  const captureFrame = useCallback((): Promise<Blob | null> => {
    const video = videoRef.current;
    if (!video || !ready) return Promise.resolve(null);

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) return Promise.resolve(null);

    context.translate(canvas.width, 0);
    context.scale(-1, 1);
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve) => {
      canvas.toBlob(resolve, "image/jpeg", 0.92);
    });
  }, [ready]);

  const capture = useCallback(async () => {
    if (capturing) return;
    setCapturing(true);
    try {
      const primary = await captureFrame();
      if (!primary) return;

      const additionalFrames: Blob[] = [];
      const additionalFrameCount = captureBurst ? 4 : 0;
      for (let index = 0; index < additionalFrameCount; index += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 320));
        const frame = await captureFrame();
        if (frame) additionalFrames.push(frame);
      }
      onCapture(primary, additionalFrames);
    } finally {
      setCapturing(false);
    }
  }, [captureBurst, captureFrame, capturing, onCapture]);

  const processing = busy || capturing;

  return (
    <div>
      <div className="relative aspect-[4/3] overflow-hidden rounded-[1.75rem] bg-ink">
        <video
          ref={videoRef}
          className="h-full w-full scale-x-[-1] object-cover"
          muted
          playsInline
        />
        {!ready && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-8 text-center text-white/70">
            <CameraOff className="h-8 w-8" />
            <p className="max-w-xs text-sm">
              {cameraError ?? "Starting your camera…"}
            </p>
          </div>
        )}
        {ready && (
          <>
            <div className="pointer-events-none absolute inset-[17%] rounded-[42%] border border-lime/80 shadow-[0_0_0_999px_rgba(16,33,28,0.16)]" />
            <span className="absolute left-5 top-5 flex items-center gap-2 rounded-full bg-ink/70 px-3 py-1.5 text-xs font-medium text-white backdrop-blur">
              <span className="h-2 w-2 rounded-full bg-lime" />
              Camera live
            </span>
            {captureBurst && (
              <span className="absolute bottom-5 left-1/2 flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full bg-ink/80 px-4 py-2 text-xs font-semibold text-white backdrop-blur">
                <MoveHorizontal className="h-4 w-4 text-lime" />
                {capturing
                  ? "Turn your head slowly"
                  : "On capture, gently turn your head"}
              </span>
            )}
          </>
        )}
      </div>

      <div className="mt-4 flex gap-3">
        <button
          type="button"
          onClick={() => void capture()}
          disabled={!ready || processing}
          className="flex flex-1 items-center justify-center gap-2 rounded-full bg-ink px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-fern disabled:cursor-not-allowed disabled:opacity-50"
        >
          {processing ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <ScanFace className="h-4 w-4" />
          )}
          {processing && captureBurst
            ? "Checking head movement…"
            : processing
              ? "Capturing…"
              : actionLabel}
        </button>
        <button
          type="button"
          onClick={() => void startCamera()}
          className="grid h-12 w-12 place-items-center rounded-full border border-ink/15 text-ink transition hover:bg-white"
          aria-label="Restart camera"
        >
          <Camera className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
