import { useQuery } from "@tanstack/react-query";
import { fetchJobDetail, fetchJobStatus } from "@/services/api";

export function useJobDetailQuery(jobId: string) {
  return useQuery({
    queryKey: ["job-detail", jobId],
    queryFn: () => fetchJobDetail(jobId),
    enabled: Boolean(jobId),
    refetchInterval: 15000,
  });
}

export function useJobStatusQuery(jobId: string) {
  return useQuery({
    queryKey: ["job-status", jobId],
    queryFn: () => fetchJobStatus(jobId),
    enabled: Boolean(jobId),
    refetchInterval: 10000,
  });
}
