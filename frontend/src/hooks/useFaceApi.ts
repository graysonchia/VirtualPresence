import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { enrollFace, getUsers, identifyFace } from "../api/client";

export function useEnrolledUsers() {
  return useQuery({
    queryKey: ["face-users"],
    queryFn: getUsers,
  });
}

export function useEnrollFace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: enrollFace,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["face-users"] });
    },
  });
}

export function useIdentifyFace() {
  return useMutation({
    mutationFn: identifyFace,
  });
}

