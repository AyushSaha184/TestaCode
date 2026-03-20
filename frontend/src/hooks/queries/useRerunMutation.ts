import { useMutation, useQueryClient } from "@tanstack/react-query";
import { pollCi, rerunJob } from "@/services/api";

export function useRerunMutation(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => rerunJob(jobId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["job-detail", jobId] });
      queryClient.invalidateQueries({ queryKey: ["job-detail", result.rerun_job_id] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function usePollCiMutation(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => pollCi(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job-detail", jobId] });
      queryClient.invalidateQueries({ queryKey: ["job-status", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
