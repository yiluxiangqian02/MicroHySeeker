import { useQuery } from "@tanstack/react-query";
import { HttpError } from "@/api/client";
import { dataApi } from "@/api/data";
import type { LatestExperimentResponse } from "@/api/types";

export const useLatestExperimentQuery = () =>
  useQuery<LatestExperimentResponse>({
    queryKey: ["latest-experiment"],
    queryFn: dataApi.getLatestExperiment,
    staleTime: 10000,
    retry: (failureCount, error) => {
      if (error instanceof HttpError && error.status === 404) {
        return false;
      }
      return failureCount < 2;
    }
  });
