import {
  Bot,
  LoaderCircle,
  LockKeyhole,
  MessageCircle,
  Mic,
  Square,
  Send,
  UserRound,
  Volume2,
  VolumeX,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "../api/client";
import {
  useConversationHistory,
  useSendConversationMessage,
} from "../hooks/useConversationApi";
import {
  useSynthesizeSpeech,
  useTranscribeAudio,
} from "../hooks/useVoiceApi";
import type { EnrolledUser } from "../types";
import type { ConversationAnimationState } from "./Avatar";

interface ChatPanelProps {
  user: EnrolledUser | null;
  detectedEmotion: string | null;
  onConversationStateChange?: (state: ConversationAnimationState) => void;
}

interface MessageInput {
  message?: string;
  audioTranscriptOf?: string;
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function ChatPanel({
  user,
  detectedEmotion,
  onConversationStateChange,
}: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isStartingRecording, setIsStartingRecording] = useState(false);
  const [isAvatarSpeaking, setIsAvatarSpeaking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const scrollAnchor = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const microphoneStream = useRef<MediaStream | null>(null);
  const recordingChunks = useRef<Blob[]>([]);
  const recordingTimer = useRef<number | null>(null);
  const avatarSpeakingTimer = useRef<number | null>(null);
  const recordingStartAttempt = useRef(0);
  const recordingStarting = useRef(false);
  const audioPlayer = useRef<HTMLAudioElement | null>(null);
  const audioUrl = useRef<string | null>(null);
  const mutedRef = useRef(isMuted);
  const mountedRef = useRef(false);

  const history = useConversationHistory(user?.id ?? null);
  const sendMessage = useSendConversationMessage(user?.id ?? null);
  const transcribe = useTranscribeAudio();
  const synthesize = useSynthesizeSpeech();

  const releaseAudio = useCallback(() => {
    audioPlayer.current?.pause();
    audioPlayer.current = null;
    if (audioUrl.current) {
      URL.revokeObjectURL(audioUrl.current);
      audioUrl.current = null;
    }
  }, []);

  const stopMicrophone = useCallback(() => {
    if (recordingTimer.current !== null) {
      window.clearTimeout(recordingTimer.current);
      recordingTimer.current = null;
    }
    microphoneStream.current?.getTracks().forEach((track) => track.stop());
    microphoneStream.current = null;
  }, []);

  const stopAndReleaseRecorder = useCallback(() => {
    if (mediaRecorderRef.current) {
      const activeRecorder = mediaRecorderRef.current;
      activeRecorder.ondataavailable = null;
      activeRecorder.onstop = null;
      mediaRecorderRef.current = null;

      if (activeRecorder.state !== "inactive") {
        try {
          activeRecorder.stop();
        } catch {
          // The recorder may have become inactive during browser teardown.
        }
      }
    }
  }, []);

  const cancelRecordingSession = useCallback(() => {
    recordingStartAttempt.current += 1;
    recordingStarting.current = false;
    stopAndReleaseRecorder();
    stopMicrophone();
    recordingChunks.current = [];
  }, [stopAndReleaseRecorder, stopMicrophone]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    scrollAnchor.current?.scrollIntoView({ behavior: "smooth" });
  }, [history.data?.count, sendMessage.isPending]);

  useEffect(() => {
    if (avatarSpeakingTimer.current !== null) {
      window.clearTimeout(avatarSpeakingTimer.current);
      avatarSpeakingTimer.current = null;
    }

    const reply = sendMessage.data?.assistant_reply;
    if (!reply) {
      setIsAvatarSpeaking(false);
      return;
    }

    setIsAvatarSpeaking(true);
    const speakingDuration = Math.min(
      8_000,
      Math.max(1_800, reply.length * 45),
    );
    avatarSpeakingTimer.current = window.setTimeout(() => {
      setIsAvatarSpeaking(false);
      avatarSpeakingTimer.current = null;
    }, speakingDuration);

    return () => {
      if (avatarSpeakingTimer.current !== null) {
        window.clearTimeout(avatarSpeakingTimer.current);
        avatarSpeakingTimer.current = null;
      }
    };
  }, [sendMessage.data?.assistant_reply]);

  const avatarConversationState: ConversationAnimationState =
    sendMessage.isPending
      ? "thinking"
      : isAvatarSpeaking
        ? "speaking"
        : "idle";

  useEffect(() => {
    onConversationStateChange?.(avatarConversationState);
  }, [avatarConversationState, onConversationStateChange]);

  useEffect(() => {
    cancelRecordingSession();
    setIsRecording(false);
    setIsStartingRecording(false);
    setIsAvatarSpeaking(false);
    releaseAudio();
    setMessage("");
    setVoiceError(null);
    sendMessage.reset();
    transcribe.reset();
    synthesize.reset();
  }, [user?.id, cancelRecordingSession, releaseAudio]);

  useEffect(() => {
    mutedRef.current = isMuted;
    if (isMuted) releaseAudio();
  }, [isMuted, releaseAudio]);

  useEffect(
    () => () => {
      cancelRecordingSession();
      if (avatarSpeakingTimer.current !== null) {
        window.clearTimeout(avatarSpeakingTimer.current);
        avatarSpeakingTimer.current = null;
      }
      releaseAudio();
    },
    [cancelRecordingSession, releaseAudio],
  );

  const playReply = useCallback(
    async (audio: Blob) => {
      if (mutedRef.current) return;
      releaseAudio();
      const url = URL.createObjectURL(audio);
      const player = new Audio(url);
      audioUrl.current = url;
      audioPlayer.current = player;
      player.onended = releaseAudio;
      try {
        await player.play();
      } catch {
        setVoiceError(
          "The reply is ready, but the browser blocked autoplay. Try unmuting again.",
        );
      }
    },
    [releaseAudio],
  );

  const sendContent = useCallback(
    (input: MessageInput) => {
      if (!user || sendMessage.isPending) return;
      setVoiceError(null);
      sendMessage.mutate(input, {
        onSuccess: (reply) => {
          setMessage("");
          if (mutedRef.current) return;
          synthesize.mutate(
            {
              text: reply.assistant_reply,
              language: reply.detected_input_language,
              user_id: user.id,
            },
            {
              onSuccess: (audio) => void playReply(audio),
            },
          );
        },
      });
    },
    [playReply, sendMessage, synthesize, user],
  );

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const content = message.trim();
    if (!content) return;
    sendContent({ message: content });
  };

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current) {
      const activeRecorder = mediaRecorderRef.current;
      if (activeRecorder.state === "recording") {
        activeRecorder.stop();
      }
    }
  }, []);

  const startRecording = async () => {
    if (recordingStarting.current || mediaRecorderRef.current) return;

    recordingStarting.current = true;
    setIsStartingRecording(true);
    setVoiceError(null);
    transcribe.reset();
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      recordingStarting.current = false;
      setIsStartingRecording(false);
      setVoiceError("This browser does not support microphone recording.");
      return;
    }

    const attempt = ++recordingStartAttempt.current;
    let acquiredStream: MediaStream | null = null;
    let mediaRecorder: MediaRecorder | null = null;

    try {
      acquiredStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      if (
        !mountedRef.current ||
        attempt !== recordingStartAttempt.current
      ) {
        acquiredStream.getTracks().forEach((track) => track.stop());
        return;
      }

      microphoneStream.current = acquiredStream;
      recordingChunks.current = [];

      const preferredType = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
      ].find((type) => MediaRecorder.isTypeSupported(type));
      const activeMediaRecorder = new MediaRecorder(
        acquiredStream,
        preferredType ? { mimeType: preferredType } : undefined,
      );
      mediaRecorder = activeMediaRecorder;
      mediaRecorderRef.current = activeMediaRecorder;

      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.ondataavailable = (event) => {
          console.debug("[voice] MediaRecorder data available", {
            sizeBytes: event.data.size,
            type: event.data.type,
          });
          if (event.data.size > 0) recordingChunks.current.push(event.data);
        };
        mediaRecorderRef.current.onstop = () => {
          if (mediaRecorderRef.current === activeMediaRecorder) {
            mediaRecorderRef.current = null;
          }

          const chunks = recordingChunks.current;
          recordingChunks.current = [];
          stopMicrophone();

          if (
            !mountedRef.current ||
            attempt !== recordingStartAttempt.current
          ) {
            return;
          }

          setIsRecording(false);
          const audio = new Blob(chunks, {
            type: activeMediaRecorder.mimeType || "audio/webm",
          });
          console.log("[voice] Recorded audio blob ready for upload", {
            blobSizeBytes: audio.size,
            chunkBytes: chunks.reduce((total, chunk) => total + chunk.size, 0),
            chunkCount: chunks.length,
            type: audio.type,
          });
          if (!audio.size) {
            setVoiceError("No audio was recorded. Please try again.");
            return;
          }
          transcribe.mutate(audio, {
            onSuccess: (result) => {
              sendContent({ audioTranscriptOf: result.text });
            },
          });
        };
      }

      activeMediaRecorder.start(250);
      setIsRecording(true);
      recordingTimer.current = window.setTimeout(stopRecording, 60_000);
    } catch {
      if (mediaRecorderRef.current === mediaRecorder) {
        stopAndReleaseRecorder();
      }
      if (microphoneStream.current === acquiredStream) {
        stopMicrophone();
      } else {
        acquiredStream?.getTracks().forEach((track) => track.stop());
      }
      if (mountedRef.current && attempt === recordingStartAttempt.current) {
        setIsRecording(false);
        setVoiceError(
          "Microphone access was blocked. Allow permission and try again.",
        );
      }
    } finally {
      if (attempt === recordingStartAttempt.current) {
        recordingStarting.current = false;
        if (mountedRef.current) setIsStartingRecording(false);
      }
    }
  };

  if (!user) {
    return (
      <section className="rounded-[2.5rem] border border-white/70 bg-white/65 p-7 shadow-panel backdrop-blur sm:p-9">
        <div className="flex min-h-52 flex-col items-center justify-center text-center">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-ink/5 text-ink/45">
            <LockKeyhole className="h-5 w-5" />
          </span>
          <h2 className="mt-4 font-display text-xl font-semibold text-ink">
            Conversation locked
          </h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-ink/50">
            Complete a verified live identification to start a personalized
            text or voice conversation.
          </p>
        </div>
      </section>
    );
  }

  const messages = history.data?.messages ?? [];
  const conversationError = history.error ?? sendMessage.error;
  const speechError = transcribe.error ?? synthesize.error;
  const voiceBusy = transcribe.isPending || synthesize.isPending;

  return (
    <section className="overflow-hidden rounded-[2.5rem] bg-white shadow-panel">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-ink/8 px-6 py-5 sm:px-8">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-2xl bg-ink text-lime">
            <MessageCircle className="h-5 w-5" />
          </span>
          <div>
            <h2 className="font-display text-lg font-semibold text-ink">
              Chat with VirtualPresence
            </h2>
            <p className="text-xs text-ink/50">
              Verified as {user.name}
              {detectedEmotion ? ` · ${detectedEmotion}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {sendMessage.data && (
            <span className="rounded-full bg-fern/10 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-fern">
              {sendMessage.data.detected_input_language}
            </span>
          )}
          <button
            type="button"
            onClick={() => setIsMuted((current) => !current)}
            className={`grid h-9 w-9 place-items-center rounded-xl transition ${
              isMuted
                ? "bg-ink/5 text-ink/40"
                : "bg-lime/25 text-fern hover:bg-lime/40"
            }`}
            aria-label={isMuted ? "Unmute spoken replies" : "Mute spoken replies"}
            title={isMuted ? "Unmute spoken replies" : "Mute spoken replies"}
          >
            {isMuted ? (
              <VolumeX className="h-4 w-4" />
            ) : (
              <Volume2 className="h-4 w-4" />
            )}
          </button>
        </div>
      </header>

      <div
        className="h-[360px] space-y-4 overflow-y-auto bg-mist/35 px-5 py-6 sm:px-8"
        aria-live="polite"
      >
        {history.isLoading && (
          <div className="flex h-full items-center justify-center gap-2 text-sm text-ink/45">
            <LoaderCircle className="h-4 w-4 animate-spin" />
            Loading conversation…
          </div>
        )}

        {!history.isLoading && messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <Bot className="h-8 w-8 text-fern" />
            <p className="mt-3 font-medium text-ink">
              Good to see you, {user.name}.
            </p>
            <p className="mt-1 text-sm text-ink/45">
              Type a message or tap the microphone to begin.
            </p>
          </div>
        )}

        {messages.map((item) => {
          const fromUser = item.role === "user";
          return (
            <div
              key={item.id}
              className={`flex items-end gap-2 ${
                fromUser ? "justify-end" : "justify-start"
              }`}
            >
              {!fromUser && (
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-xl bg-ink text-lime">
                  <Bot className="h-3.5 w-3.5" />
                </span>
              )}
              <div
                className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                  fromUser
                    ? "rounded-br-md bg-ink text-white"
                    : "rounded-bl-md border border-ink/5 bg-white text-ink shadow-sm"
                }`}
              >
                {item.content}
              </div>
              {fromUser && (
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-xl bg-fern/10 text-fern">
                  <UserRound className="h-3.5 w-3.5" />
                </span>
              )}
            </div>
          );
        })}

        {sendMessage.isPending && (
          <div className="flex items-end gap-2">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-xl bg-ink text-lime">
              <Bot className="h-3.5 w-3.5" />
            </span>
            <span className="flex items-center gap-2 rounded-2xl rounded-bl-md bg-white px-4 py-3 text-xs text-ink/45 shadow-sm">
              <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
              Thinking…
            </span>
          </div>
        )}
        <div ref={scrollAnchor} />
      </div>

      <form
        onSubmit={submit}
        className="border-t border-ink/8 bg-white px-5 py-5 sm:px-8"
      >
        {conversationError && (
          <p className="mb-3 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700">
            {errorMessage(
              conversationError,
              "The assistant could not respond. Please try again.",
            )}
          </p>
        )}
        {(voiceError || speechError) && (
          <p className="mb-3 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">
            {voiceError ??
              errorMessage(
                speechError,
                "Voice processing failed. You can continue using text.",
              )}
          </p>
        )}
        <div className="flex items-end gap-2 sm:gap-3">
          <label className="min-w-0 flex-1">
            <span className="sr-only">Message</span>
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              rows={2}
              maxLength={4000}
              disabled={isRecording}
              placeholder={
                isRecording
                  ? "Listening…"
                  : `Message or speak as ${user.name}…`
              }
              className="block w-full resize-none rounded-2xl border border-ink/10 bg-mist/45 px-4 py-3 text-sm leading-5 text-ink outline-none transition placeholder:text-ink/30 focus:border-fern disabled:opacity-50"
            />
          </label>
          <button
            type="button"
            onClick={
              isRecording ? stopRecording : () => void startRecording()
            }
            disabled={
              isStartingRecording ||
              (!isRecording && (transcribe.isPending || sendMessage.isPending))
            }
            className={`grid h-11 w-11 shrink-0 place-items-center rounded-2xl transition disabled:cursor-not-allowed disabled:opacity-35 ${
              isRecording
                ? "animate-pulse bg-coral text-white"
                : "bg-fern/10 text-fern hover:bg-fern/20"
            }`}
            aria-label={
              isStartingRecording
                ? "Starting microphone"
                : isRecording
                  ? "Stop recording"
                  : "Record voice message"
            }
            title={
              isStartingRecording
                ? "Starting microphone"
                : isRecording
                  ? "Stop recording"
                  : "Record voice message"
            }
          >
            {isStartingRecording ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : isRecording ? (
              <Square className="h-4 w-4 fill-current" />
            ) : (
              <Mic className="h-4 w-4" />
            )}
          </button>
          <button
            type="submit"
            disabled={
              !message.trim() ||
              sendMessage.isPending ||
              transcribe.isPending ||
              isRecording
            }
            className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-ink text-lime transition hover:bg-fern disabled:cursor-not-allowed disabled:opacity-35"
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-ink/35">
          <span>Enter to send · Shift + Enter for a new line</span>
          <span className={isRecording ? "font-semibold text-coral" : ""}>
            {isRecording
              ? "Listening · tap stop when finished"
              : transcribe.isPending
                ? "Transcribing locally…"
                : sendMessage.isPending && transcribe.data
                  ? `Heard: “${transcribe.data.text}”`
                  : synthesize.isPending
                    ? "Preparing spoken reply…"
                    : voiceBusy
                      ? "Processing voice…"
                      : "Voice ready"}
          </span>
        </div>
      </form>
    </section>
  );
}
