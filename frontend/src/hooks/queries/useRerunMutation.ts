import { useMutation, useQueryClient } from "@tanstack/react-query";
import { rerunJob } from "@/services/api";

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
