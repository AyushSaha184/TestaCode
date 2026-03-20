import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchJobFeedback, submitJobFeedback } from "@/services/api";
import type { JobFeedbackPayload } from "@/types/api";

export function useJobFeedbackQuery(jobId: string) {
  return useQuery({
    queryKey: ["job-feedback", jobId],
    queryFn: () => fetchJobFeedback(jobId),
    enabled: Boolean(jobId),
  });
}

export function useSubmitJobFeedbackMutation(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: JobFeedbackPayload) => submitJobFeedback(jobId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job-feedback", jobId] });
      queryClient.invalidateQueries({ queryKey: ["job-detail", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
