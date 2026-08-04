import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  enrollFace,
  getEdgeBenchmark,
  getUsers,
  identifyFace,
} from "../api/client";

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

export function useEdgeBenchmark() {
  return useQuery({
    queryKey: ["edge-face-benchmark"],
    queryFn: getEdgeBenchmark,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
