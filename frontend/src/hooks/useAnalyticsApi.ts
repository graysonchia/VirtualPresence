import { useQuery } from "@tanstack/react-query";

import {
  getAnalyticsOverview,
  getEmotionDistribution,
  getRecognitionTrends,
  getUsagePatterns,
} from "../api/analytics";

export function useAnalyticsOverview() {
  return useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: getAnalyticsOverview,
  });
}

export function useRecognitionTrends(days: number) {
  return useQuery({
    queryKey: ["analytics", "recognition-trends", days],
    queryFn: () => getRecognitionTrends(days),
  });
}

export function useEmotionDistribution() {
  return useQuery({
    queryKey: ["analytics", "emotion-distribution"],
    queryFn: getEmotionDistribution,
  });
}

export function useUsagePatterns() {
  return useQuery({
    queryKey: ["analytics", "usage-patterns"],
    queryFn: getUsagePatterns,
  });
}
