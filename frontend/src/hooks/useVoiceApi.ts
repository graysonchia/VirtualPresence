import { useMutation } from "@tanstack/react-query";

import { synthesizeSpeech, transcribeAudio } from "../api/voice";

export function useTranscribeAudio() {
  return useMutation({
    mutationFn: transcribeAudio,
  });
}

export function useSynthesizeSpeech() {
  return useMutation({
    mutationFn: synthesizeSpeech,
  });
}
