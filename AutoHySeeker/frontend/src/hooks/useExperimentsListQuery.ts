import { useQuery } from '@tanstack/react-query';
import { experimentsApi } from '../api/experiments';

export function useExperimentsListQuery() {
  return useQuery({
    queryKey: ['experiments', 'list'],
    queryFn: () => experimentsApi.list(),
    staleTime: 30_000,
  });
}
