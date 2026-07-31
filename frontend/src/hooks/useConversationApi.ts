import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getConversationHistory,
  sendConversationMessage,
} from "../api/conversation";

export function useConversationHistory(userId: string | null) {
  return useQuery({
    queryKey: ["conversation-history", userId],
    queryFn: () => getConversationHistory(userId!),
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
