export type AvatarEmotion =
  | "happy"
  | "sad"
  | "angry"
  | "surprised"
  | "neutral"
  | "fearful"
  | "disgusted";

export type ConversationAnimationState = "idle" | "thinking" | "speaking";

export interface AvatarExpression {
  browLift: number;
  browSlant: number;
  eyeOpenness: number;
  headNod: number;
  headTilt: number;
  mouthCurve: number;
  mouthOpen: number;
}

export const NEUTRAL_EXPRESSION: AvatarExpression = {
  browLift: 0,
  browSlant: 0,
  eyeOpenness: 1,
  headNod: 0,
  headTilt: 0,
  mouthCurve: 0.08,
  mouthOpen: 0.02,
};

export const EMOTION_EXPRESSIONS: Record<
  AvatarEmotion,
  AvatarExpression
> = {
  neutral: NEUTRAL_EXPRESSION,
  happy: {
    browLift: 0.1,
    browSlant: 0.08,
    eyeOpenness: 0.78,
    headNod: -0.03,
    headTilt: 0.04,
    mouthCurve: 0.82,
    mouthOpen: 0.12,
  },
  sad: {
    browLift: 0.08,
    browSlant: -0.48,
    eyeOpenness: 0.72,
    headNod: 0.13,
    headTilt: -0.08,
    mouthCurve: -0.68,
    mouthOpen: 0.03,
  },
  angry: {
    browLift: -0.22,
    browSlant: 0.58,
    eyeOpenness: 0.68,
    headNod: -0.08,
    headTilt: 0,
    mouthCurve: -0.38,
    mouthOpen: 0.06,
  },
  surprised: {
    browLift: 0.52,
    browSlant: 0,
    eyeOpenness: 1.28,
    headNod: -0.09,
    headTilt: 0.03,
    mouthCurve: 0,
    mouthOpen: 0.72,
  },
  fearful: {
    browLift: 0.34,
    browSlant: -0.28,
    eyeOpenness: 1.18,
    headNod: 0.04,
    headTilt: -0.09,
    mouthCurve: -0.22,
    mouthOpen: 0.3,
  },
  disgusted: {
    browLift: -0.12,
    browSlant: 0.25,
    eyeOpenness: 0.62,
    headNod: -0.05,
    headTilt: 0.1,
    mouthCurve: -0.48,
    mouthOpen: 0.08,
  },
};

export function normalizeEmotion(emotion: string | null): AvatarEmotion {
  const normalized = emotion?.trim().toLowerCase();
  return normalized && normalized in EMOTION_EXPRESSIONS
    ? (normalized as AvatarEmotion)
    : "neutral";
}

export function expressionForEmotion(
  emotion: string | null,
): AvatarExpression {
  return EMOTION_EXPRESSIONS[normalizeEmotion(emotion)];
}
