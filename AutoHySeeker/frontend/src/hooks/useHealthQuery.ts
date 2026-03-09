import { useQuery } from "@tanstack/react-query";
import { healthApi } from "@/api/health";
import type { HealthResponse } from "@/api/types";

export const useHealthQuery = () =>
  useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: healthApi.check,
    staleTime: 15000,
    refetchInterval: 30000
  });

