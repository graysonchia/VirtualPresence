export type UserStatus = "active" | "inactive";
export type VoiceGender = "male" | "female";
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
  preferred_voice_gender: VoiceGender;
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

export interface AnalyticsOverview {
  total_users: number;
  total_sessions: number;
  total_messages: number;
  total_recognition_attempts: number;
  average_session_length_seconds: number;
  average_messages_per_session: number;
  recognition_success_rate: number;
  average_match_confidence: number;
  liveness_pass_rate: number;
  liveness_fail_rate: number;
  spoof_detection_count: number;
  total_memory_facts: number;
  referenced_memory_facts: number;
  average_referenced_facts_per_session: number;
}

export interface RecognitionTrendPoint {
  date: string;
  total_attempts: number;
  recognized_count: number;
  spoof_detection_count: number;
  average_match_confidence: number | null;
  liveness_pass_rate: number | null;
  liveness_fail_rate: number | null;
  low_confidence_count: number;
  medium_confidence_count: number;
  high_confidence_count: number;
}

export interface RecognitionTrendsResponse {
  days: number;
  start_date: string;
  end_date: string;
  points: RecognitionTrendPoint[];
}

export interface EmotionDistributionItem {
  emotion: string;
  count: number;
  percentage: number;
}

export interface EmotionDistributionResponse {
  total_observations: number;
  emotions: EmotionDistributionItem[];
}

export interface DailyUsagePoint {
  date: string;
  sessions: number;
  messages: number;
  average_messages_per_session: number;
  average_session_length_seconds: number;
}

export interface HourlyUsagePoint {
  hour: number;
  sessions: number;
  messages: number;
}

export interface UsagePatternsResponse {
  timezone: string;
  total_sessions: number;
  total_messages: number;
  average_messages_per_session: number;
  average_session_length_seconds: number;
  most_active_hour: number | null;
  daily: DailyUsagePoint[];
  hourly: HourlyUsagePoint[];
}
