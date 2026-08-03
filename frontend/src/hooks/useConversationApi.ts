import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getConversationHistory,
  sendConversationMessage,
  startNewConversation,
} from "../api/conversation";
import type { ConversationHistoryResponse } from "../types";

export function useConversationHistory(userId: string | null) {
  return useQuery({
    queryKey: ["conversation-history", userId],
    queryFn: () => getConversationHistory(userId!, true),
    enabled: Boolean(userId),
  });
}

export function useSendConversationMessage(userId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: {
      message?: string;
      audioTranscriptOf?: string;
    }) => sendConversationMessage({ userId: userId!, ...input }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["conversation-history", userId],
      });
    },
  });
}

export function useStartNewConversation(userId: string | null) {
  const queryClient = useQueryClient();
  const queryKey = ["conversation-history", userId] as const;

  return useMutation({
    mutationFn: () => startNewConversation(userId!),
    onSuccess: async () => {
      queryClient.setQueryData<ConversationHistoryResponse>(
        queryKey,
        (current) =>
          current
            ? { ...current, messages: [], count: 0 }
            : current,
      );
      await queryClient.invalidateQueries({ queryKey });
    },
  });
}
