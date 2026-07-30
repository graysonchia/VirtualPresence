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
