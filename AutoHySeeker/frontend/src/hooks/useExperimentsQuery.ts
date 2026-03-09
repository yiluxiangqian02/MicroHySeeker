import { useQuery } from "@tanstack/react-query";
import { dataApi } from "@/api/data";
import type { ExperimentsResponse } from "@/api/types";

export const useExperimentsQuery = (limit = 10) =>
  useQuery<ExperimentsResponse>({
    queryKey: ["experiments", limit],
    queryFn: () => dataApi.listExperiments(limit),
    staleTime: 10000
  });

