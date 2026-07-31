import type {
  ConversationHistoryResponse,
  ConversationMessageResponse,
} from "../types";
import { request } from "./client";

export function getConversationHistory(
  userId: string,
): Promise<ConversationHistoryResponse> {
  return request<ConversationHistoryResponse>(
    `/conversation/users/${encodeURIComponent(userId)}/history`,
  );
}

export function sendConversationMessage(input: {
  userId: string;
  message?: string;
  audioTranscriptOf?: string;
}): Promise<ConversationMessageResponse> {
  return request<ConversationMessageResponse>("/conversation/message", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: input.userId,
      message: input.message,
      audio_transcript_of: input.audioTranscriptOf,
    }),
  });
}
