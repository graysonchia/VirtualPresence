export type UserStatus = "active" | "inactive";
export type RecognitionOutcome =
  | "recognized"
  | "unrecognized"
  | "spoof_detected";

export interface EnrolledUser {
  id: string;
  name: string;
  email: string;
  enrolled_at: string;
  preferred_language: string;
  status: UserStatus;
}

export interface EnrollmentResponse {
  message: string;
  user: EnrolledUser;
  embedding_id: string;
}

export interface IdentificationResponse {
  outcome: RecognitionOutcome;
  confidence: number;
  user: EnrolledUser | null;
  faces_detected: number;
  detected_emotion: string | null;
  emotion_confidence: number | null;
  emotion_scores: Record<string, number>;
  is_live: boolean;
  liveness_confidence: number;
}

export interface UserListResponse {
  users: EnrolledUser[];
  count: number;
}

export type ConversationRole = "user" | "assistant";

export interface ConversationHistoryMessage {
  id: string;
  session_id: string;
  role: ConversationRole;
  content: string;
  timestamp: string;
}

export interface ConversationHistoryResponse {
  user_id: string;
  user_name: string;
  messages: ConversationHistoryMessage[];
  count: number;
}

export interface ConversationMessageResponse {
  user_id: string;
  session_id: string;
  assistant_reply: string;
  detected_input_language: string;
  input_mode: "text" | "voice";
  timestamp: string;
}

export interface TranscriptionResponse {
  text: string;
  detected_language: string;
  language_confidence: number;
}
