import { useQuery } from "@tanstack/react-query";
import { fetchExtraction } from "@/lib/api";

export function useExtraction(id: string) {
  return useQuery({
    queryKey: ["extraction", id],
    queryFn: () => fetchExtraction(id),
    enabled: !!id,
  });
}
