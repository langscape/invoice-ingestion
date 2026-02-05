import { useQuery } from "@tanstack/react-query";
import { fetchReviewQueue } from "@/lib/api";
import type { QueueFilters } from "@/lib/types";

export function useReviewQueue(filters: QueueFilters) {
  const params: Record<string, string> = {};
  if (filters.commodityType) params.commodity = filters.commodityType;
  if (filters.confidenceTier) params.confidence_tier = filters.confidenceTier;

  return useQuery({
    queryKey: ["reviewQueue", filters],
    queryFn: () => fetchReviewQueue(params),
    refetchInterval: 30000,
  });
}
