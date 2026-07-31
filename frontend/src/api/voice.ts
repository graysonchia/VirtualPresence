import type { TranscriptionResponse } from "../types";
import { request, requestBlob } from "./client";

export function transcribeAudio(audio: Blob): Promise<TranscriptionResponse> {
  const form = new FormData();
  const extension = audio.type.includes("ogg") ? "ogg" : "webm";
  form.append("audio", audio, `voice-recording.${extension}`);
  return request<TranscriptionResponse>("/voice/transcribe", {
    method: "POST",
    body: form,
  });
}

export function synthesizeSpeech(input: {
  text: string;
  language: string;
}): Promise<Blob> {
  return requestBlob("/voice/synthesize", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
}
