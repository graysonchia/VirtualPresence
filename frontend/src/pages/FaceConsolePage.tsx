import {
  CheckCircle2,
  ScanFace,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  XCircle,
} from "lucide-react";
import { useCallback, useState } from "react";

import { ApiError } from "../api/client";
import { UserList } from "../components/UserList";
import { WebcamCapture } from "../components/WebcamCapture";
import {
  useEnrollFace,
  useEnrolledUsers,
  useIdentifyFace,
} from "../hooks/useFaceApi";

type Mode = "identify" | "enroll";

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}

export function FaceConsolePage() {
  const [mode, setMode] = useState<Mode>("identify");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [language, setLanguage] = useState("en");
  const enroll = useEnrollFace();
  const identify = useIdentifyFace();
  const users = useEnrolledUsers();

  const clearResults = () => {
    enroll.reset();
    identify.reset();
  };

  const selectMode = (nextMode: Mode) => {
    clearResults();
    setMode(nextMode);
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
        identify.mutate({ image, frames: additionalFrames });
      }
    },
    [email, enroll, identify, language, mode, name],
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

  return (
    <main className="min-h-screen px-5 py-6 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-7xl">
        <header className="flex items-center justify-between py-3">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-ink text-lime">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="font-display text-lg font-bold leading-none text-ink">
                VirtualPresence
              </p>
              <p className="mt-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-fern">
                Recognition console
              </p>
            </div>
          </div>
          <span className="hidden items-center gap-2 rounded-full border border-ink/10 bg-white/60 px-4 py-2 text-xs font-medium text-ink/60 sm:flex">
            <ShieldCheck className="h-4 w-4 text-fern" />
            Phase 2 · Local processing
          </span>
        </header>

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
                    mode === "enroll" ? "Capture & enroll" : "Identify me"
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
      </div>
    </main>
  );
}
