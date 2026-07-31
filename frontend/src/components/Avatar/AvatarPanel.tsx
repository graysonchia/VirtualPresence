import { Canvas } from "@react-three/fiber";
import { Activity, Brain, MessageCircleMore, Sparkles } from "lucide-react";

import { Avatar } from "./Avatar";
import {
  normalizeEmotion,
  type ConversationAnimationState,
} from "./expressions";

interface AvatarPanelProps {
  conversationState: ConversationAnimationState;
  emotion: string | null;
  userName: string;
}

const STATE_LABELS: Record<ConversationAnimationState, string> = {
  idle: "Present",
  thinking: "Thinking",
  speaking: "Speaking",
};

function StateIcon({
  state,
}: {
  state: ConversationAnimationState;
}) {
  if (state === "thinking") return <Brain className="h-3.5 w-3.5" />;
  if (state === "speaking") {
    return <MessageCircleMore className="h-3.5 w-3.5" />;
  }
  return <Activity className="h-3.5 w-3.5" />;
}

export function AvatarPanel({
  conversationState,
  emotion,
  userName,
}: AvatarPanelProps) {
  const normalizedEmotion = normalizeEmotion(emotion);

  return (
    <section className="relative min-h-[440px] overflow-hidden rounded-[2.5rem] bg-ink shadow-panel lg:min-h-[590px]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_38%,rgba(200,255,124,0.2),transparent_36%),linear-gradient(155deg,rgba(255,255,255,0.05),transparent_48%)]" />
      <div className="absolute left-6 right-6 top-6 z-10 flex items-start justify-between gap-3">
        <div>
          <span className="inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-lime/75">
            <Sparkles className="h-3.5 w-3.5" />
            Virtual presence
          </span>
          <h2 className="mt-2 font-display text-xl font-semibold text-white">
            {userName}&apos;s avatar
          </h2>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-bold ${
            conversationState === "speaking"
              ? "border-lime/35 bg-lime/15 text-lime"
              : conversationState === "thinking"
                ? "border-white/20 bg-white/10 text-white/75"
                : "border-fern/50 bg-fern/25 text-lime/85"
          }`}
        >
          <StateIcon state={conversationState} />
          {STATE_LABELS[conversationState]}
        </span>
      </div>

      <div className="absolute inset-0">
        <Canvas
          camera={{ position: [0, 0.15, 5.25], fov: 34 }}
          dpr={[1, 1.75]}
          gl={{ alpha: true, antialias: true }}
          fallback={
            <div className="grid h-full place-items-center px-8 text-center text-sm text-white/60">
              3D rendering is unavailable in this browser.
            </div>
          }
        >
          <ambientLight intensity={1.35} />
          <directionalLight
            position={[3.5, 4.5, 4]}
            intensity={2.2}
            color="#fff4df"
          />
          <pointLight
            position={[-3, 1, 2.5]}
            intensity={7}
            color="#79e6b4"
          />
          <Avatar
            emotion={normalizedEmotion}
            conversationState={conversationState}
          />
        </Canvas>
      </div>

      <div className="absolute bottom-5 left-5 right-5 z-10 flex items-center justify-between rounded-2xl border border-white/10 bg-black/15 px-4 py-3 backdrop-blur-md">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">
            Expression
          </p>
          <p className="mt-0.5 text-sm font-semibold capitalize text-white">
            {normalizedEmotion}
          </p>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-white/45">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-lime" />
          Emotion synced
        </div>
      </div>
    </section>
  );
}
