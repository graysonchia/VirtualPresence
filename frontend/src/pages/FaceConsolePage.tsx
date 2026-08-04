import {
  CheckCircle2,
  Cpu,
  Gauge,
  HardDrive,
  LockKeyhole,
  ScanFace,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { lazy, Suspense, useCallback, useState } from "react";

import { ApiError } from "../api/client";
import type { ConversationAnimationState } from "../components/Avatar";
import { AppHeader } from "../components/AppHeader";
import type { AppView } from "../components/AppHeader";
import { ChatPanel } from "../components/ChatPanel";
import { ChatPanelErrorBoundary } from "../components/ChatPanelErrorBoundary";
import { UserList } from "../components/UserList";
import { WebcamCapture } from "../components/WebcamCapture";
import {
  useEnrollFace,
  useEdgeBenchmark,
  useEnrolledUsers,
  useIdentifyFace,
} from "../hooks/useFaceApi";

type Mode = "identify" | "enroll";

interface FaceConsolePageProps {
  onNavigate: (view: AppView) => void;
}

const AvatarPanel = lazy(() =>
  import("../components/Avatar/AvatarPanel").then((module) => ({
    default: module.AvatarPanel,
  })),
);

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}

export function FaceConsolePage({ onNavigate }: FaceConsolePageProps) {
  const [mode, setMode] = useState<Mode>("identify");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [language, setLanguage] = useState("en");
  const [edgeMode, setEdgeMode] = useState(false);
  const [conversationAnimation, setConversationAnimation] =
    useState<ConversationAnimationState>("idle");
  const enroll = useEnrollFace();
  const identify = useIdentifyFace();
  const edgeBenchmark = useEdgeBenchmark();
  const users = useEnrolledUsers();

  const clearResults = () => {
    enroll.reset();
    identify.reset();
  };

  const selectMode = (nextMode: Mode) => {
    clearResults();
    setMode(nextMode);
  };

  const toggleEdgeMode = () => {
    clearResults();
    setEdgeMode((enabled) => !enabled);
  };

  const handleCapture = useCallback(
    (image: Blob, additionalFrames: Blob[]) => {
      if (mode === "enroll") {
        if (!name.trim()) return;
        enroll.mutate({
          image,
          name: name.trim(),
          email: email.trim() || undefined,
          preferredLanguage: language,
        });
      } else {
        identify.mutate({ image, frames: additionalFrames, edgeMode });
      }
    },
    [edgeMode, email, enroll, identify, language, mode, name],
  );

  const activeMutation = mode === "enroll" ? enroll : identify;
  const result =
    enroll.data?.message ??
    (identify.data?.outcome === "spoof_detected"
      ? identify.data.user
        ? `Possible match: ${identify.data.user.name}. Verification failed.`
        : "Verification failed. This capture may be a photo or screen."
      : identify.data?.outcome === "recognized"
        ? `Welcome back, ${identify.data.user?.name}.`
        : identify.data
          ? "No enrolled face matched this capture."
          : null);
  const error = activeMutation.error
    ? errorMessage(activeMutation.error)
    : null;
  const verificationFailed =
    identify.data?.outcome === "spoof_detected";
  const recognizedUser =
    identify.data?.outcome === "recognized" && identify.data.is_live
      ? identify.data.user
      : null;

  return (
    <main className="min-h-screen px-5 py-6 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-7xl">
        <AppHeader currentView="console" onNavigate={onNavigate} />

        <section className="grid gap-7 pb-10 pt-8 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="overflow-hidden rounded-[2.5rem] bg-white shadow-panel">
            <div className="grid lg:grid-cols-[0.84fr_1.16fr]">
              <div className="flex flex-col justify-between bg-ink p-7 text-white sm:p-10">
                <div>
                  <span className="inline-flex items-center gap-2 rounded-full border border-white/15 px-3 py-1.5 text-xs text-white/70">
                    <ScanFace className="h-3.5 w-3.5 text-lime" />
                    Face recognition
                  </span>
                  <h1 className="mt-8 font-display text-4xl font-semibold leading-[1.05] sm:text-5xl">
                    A familiar face is all it takes.
                  </h1>
                  <p className="mt-5 max-w-md text-sm leading-6 text-white/58">
                    Enroll once, then test identity matching directly from your
                    browser camera. Keep one face centered in clear, even light.
                  </p>
                </div>

                <div className="mt-10 rounded-3xl border border-white/10 bg-white/[0.06] p-4">
                  <p className="text-xs font-medium text-white/45">
                    Recognition model
                  </p>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-sm font-semibold">
                      YuNet · SFace · FER+
                    </span>
                    <span className="rounded-full bg-lime/15 px-2.5 py-1 text-[11px] font-bold text-lime">
                      READY
                    </span>
                  </div>
                </div>

                <div className="mt-4 rounded-3xl border border-white/10 bg-white/[0.06] p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="flex items-center gap-2 text-xs font-semibold text-white/75">
                        <Cpu className="h-3.5 w-3.5 text-lime" />
                        Edge mode
                      </p>
                      <p className="mt-1 text-[11px] leading-4 text-white/40">
                        Local INT8 SFace demonstration
                      </p>
                    </div>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={edgeMode}
                      aria-label="Use edge-optimized face identification"
                      onClick={toggleEdgeMode}
                      className={`relative h-7 w-12 rounded-full transition ${
                        edgeMode ? "bg-lime" : "bg-white/15"
                      }`}
                    >
                      <span
                        className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow-sm transition ${
                          edgeMode ? "left-6" : "left-1"
                        }`}
                      />
                    </button>
                  </div>

                  {edgeBenchmark.data ? (
                    <div className="mt-4 grid grid-cols-[1fr_auto_auto] gap-x-3 gap-y-2 text-[10px]">
                      <span className="text-white/35">Metric</span>
                      <span className="text-right text-white/35">Standard</span>
                      <span className="text-right font-semibold text-lime">Edge</span>
                      <span className="flex items-center gap-1.5 text-white/55">
                        <HardDrive className="h-3 w-3" /> Model
                      </span>
                      <span>{edgeBenchmark.data.standard.model_size_mb.toFixed(1)} MB</span>
                      <span className="text-right text-lime">
                        {edgeBenchmark.data.edge_optimized.model_size_mb.toFixed(1)} MB
                      </span>
                      <span className="flex items-center gap-1.5 text-white/55">
                        <Gauge className="h-3 w-3" /> Latency
                      </span>
                      <span>{edgeBenchmark.data.standard.mean_latency_ms.toFixed(1)} ms</span>
                      <span className="text-right text-lime">
                        {edgeBenchmark.data.edge_optimized.mean_latency_ms.toFixed(1)} ms
                      </span>
                      <span className="flex items-center gap-1.5 text-white/55">
                        <ScanFace className="h-3 w-3" /> Accuracy*
                      </span>
                      <span>
                        {edgeBenchmark.data.standard.accuracy_percent === null
                          ? "—"
                          : `${edgeBenchmark.data.standard.accuracy_percent.toFixed(1)}%`}
                      </span>
                      <span className="text-right text-lime">
                        {edgeBenchmark.data.edge_optimized.accuracy_percent === null
                          ? "—"
                          : `${edgeBenchmark.data.edge_optimized.accuracy_percent.toFixed(1)}%`}
                      </span>
                    </div>
                  ) : (
                    <p className="mt-3 text-[10px] text-white/35">
                      {edgeBenchmark.isLoading
                        ? "Measuring local models…"
                        : "Benchmark unavailable until face models are installed."}
                    </p>
                  )}
                  <p className="mt-3 flex gap-1.5 text-[10px] leading-4 text-white/35">
                    <LockKeyhole className="mt-0.5 h-3 w-3 shrink-0" />
                    Raw frames stay inside the device boundary in a real edge
                    deployment. This demo runs both paths on this machine.
                  </p>
                  <p className="mt-1 text-[9px] text-white/25">
                    *Cosine fidelity to FP32; not population-level accuracy.
                  </p>
                </div>
              </div>

              <div className="p-6 sm:p-9">
                <div className="mb-6 grid grid-cols-2 rounded-full bg-mist p-1">
                  {(["identify", "enroll"] as const).map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => selectMode(item)}
                      className={`rounded-full px-4 py-2.5 text-sm font-semibold capitalize transition ${
                        mode === item
                          ? "bg-white text-ink shadow-sm"
                          : "text-ink/45 hover:text-ink"
                      }`}
                    >
                      {item}
                    </button>
                  ))}
                </div>

                {mode === "enroll" && (
                  <div className="mb-5 grid gap-3 sm:grid-cols-2">
                    <label className="sm:col-span-2">
                      <span className="mb-1.5 block text-xs font-semibold text-ink/55">
                        Name
                      </span>
                      <input
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        placeholder="Ada Lovelace"
                        className="w-full rounded-2xl border border-ink/10 bg-mist/60 px-4 py-3 text-sm outline-none transition placeholder:text-ink/25 focus:border-fern"
                      />
                    </label>
                    <label>
                      <span className="mb-1.5 block text-xs font-semibold text-ink/55">
                        Email (optional)
                      </span>
                      <input
                        type="email"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        placeholder="ada@example.com"
                        className="w-full rounded-2xl border border-ink/10 bg-mist/60 px-4 py-3 text-sm outline-none transition placeholder:text-ink/25 focus:border-fern"
                      />
                    </label>
                    <label>
                      <span className="mb-1.5 block text-xs font-semibold text-ink/55">
                        Language
                      </span>
                      <select
                        value={language}
                        onChange={(event) => setLanguage(event.target.value)}
                        className="w-full rounded-2xl border border-ink/10 bg-mist/60 px-4 py-3 text-sm outline-none focus:border-fern"
                      >
                        <option value="en">English</option>
                        <option value="ms">Bahasa Melayu</option>
                        <option value="zh">中文</option>
                      </select>
                    </label>
                  </div>
                )}

                <WebcamCapture
                  busy={activeMutation.isPending}
                  captureBurst={mode === "identify"}
                  actionLabel={
                    mode === "enroll"
                      ? "Capture & enroll"
                      : edgeMode
                        ? "Identify on edge"
                        : "Identify me"
                  }
                  onCapture={handleCapture}
                />
                {mode === "enroll" && !name.trim() && (
                  <p className="mt-3 text-center text-xs text-coral">
                    Enter a name before capturing.
                  </p>
                )}

                {(result || error) && (
                  <div
                    className={`mt-4 flex items-start gap-3 rounded-2xl p-4 text-sm ${
                      error || verificationFailed
                        ? "bg-red-50 text-red-800"
                        : "bg-lime/20 text-ink"
                    }`}
                  >
                    {error || verificationFailed ? (
                      <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
                    ) : (
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-fern" />
                    )}
                    <div>
                      <p className="font-semibold">{error ?? result}</p>
                      {identify.data && (
                        <>
                          <p className="mt-1 text-xs opacity-65">
                            Match confidence:{" "}
                            {(identify.data.confidence * 100).toFixed(1)}% ·{" "}
                            {identify.data.faces_detected} face(s)
                          </p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <span
                              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold ${
                                identify.data.is_live
                                  ? "bg-fern/10 text-fern"
                                  : "bg-red-100 text-red-700"
                              }`}
                            >
                              {identify.data.is_live ? (
                                <ShieldCheck className="h-3.5 w-3.5" />
                              ) : (
                                <ShieldAlert className="h-3.5 w-3.5" />
                              )}
                              {identify.data.is_live
                                ? "Live"
                                : "Verification failed"}{" "}
                              ·{" "}
                              {(
                                identify.data.liveness_confidence * 100
                              ).toFixed(0)}
                              %
                            </span>
                            {identify.data.detected_emotion && (
                              <span className="rounded-full bg-white/70 px-2.5 py-1 text-[11px] font-bold capitalize text-ink/70">
                                {identify.data.detected_emotion} ·{" "}
                                {(
                                  (identify.data.emotion_confidence ?? 0) * 100
                                ).toFixed(0)}
                                %
                              </span>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <UserList
            users={users.data?.users ?? []}
            loading={users.isLoading}
          />
        </section>
        <div className="pb-12">
          {recognizedUser ? (
            <div className="grid items-stretch gap-7 lg:grid-cols-[minmax(320px,0.72fr)_minmax(0,1.28fr)]">
              <Suspense
                fallback={
                  <div className="grid min-h-[440px] place-items-center rounded-[2.5rem] bg-ink text-sm text-white/55 shadow-panel lg:min-h-[590px]">
                    Preparing virtual presence…
                  </div>
                }
              >
                <AvatarPanel
                  userName={recognizedUser.name}
                  emotion={identify.data?.detected_emotion ?? null}
                  conversationState={conversationAnimation}
                />
              </Suspense>
              <ChatPanelErrorBoundary key={recognizedUser.id}>
                <ChatPanel
                  user={recognizedUser}
                  detectedEmotion={identify.data?.detected_emotion ?? null}
                  onConversationStateChange={setConversationAnimation}
                />
              </ChatPanelErrorBoundary>
            </div>
          ) : (
            <ChatPanelErrorBoundary key="locked">
              <ChatPanel
                user={null}
                detectedEmotion={identify.data?.detected_emotion ?? null}
                onConversationStateChange={setConversationAnimation}
              />
            </ChatPanelErrorBoundary>
          )}
        </div>
      </div>
    </main>
  );
}
