import type {
  AnalyticsOverview,
  EmotionDistributionResponse,
  RecognitionTrendsResponse,
  UsagePatternsResponse,
} from "../types";
import { request } from "./client";

export function getAnalyticsOverview(): Promise<AnalyticsOverview> {
  return request<AnalyticsOverview>("/analytics/overview");
}

export function getRecognitionTrends(
  days: number,
): Promise<RecognitionTrendsResponse> {
  return request<RecognitionTrendsResponse>(
    `/analytics/recognition-trends?days=${days}`,
  );
}

export function getEmotionDistribution(): Promise<EmotionDistributionResponse> {
  return request<EmotionDistributionResponse>(
    "/analytics/emotion-distribution",
  );
}

export function getUsagePatterns(): Promise<UsagePatternsResponse> {
  return request<UsagePatternsResponse>("/analytics/usage-patterns");
}
