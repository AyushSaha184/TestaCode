import { apiClient } from "@/services/http";
import type {
  GeneratePayload,
  GenerationResponse,
  JobFeedback,
  JobFeedbackPayload,
  JobDetail,
  JobsQueryParams,
  JobStatusView,
  JobSummary,
  RerunResult,
} from "@/types/api";

export async function generateTests(payload: GeneratePayload): Promise<GenerationResponse> {
  const formData = new FormData();
  formData.append("input_mode", payload.input_mode);
  formData.append("user_prompt", payload.user_prompt);

  if (payload.code_content) formData.append("code_content", payload.code_content);
  if (payload.filename) formData.append("filename", payload.filename);
  if (payload.language) formData.append("language", payload.language);
  if (payload.upload_file) formData.append("upload_file", payload.upload_file);
  if (typeof payload.auto_commit_enabled === "boolean") {
    formData.append("auto_commit_enabled", String(payload.auto_commit_enabled));
  }

  const { data } = await apiClient.post<GenerationResponse>("/generate", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 0,
  });
  return data;
}

export async function fetchJobs(params: JobsQueryParams): Promise<JobSummary[]> {
  const { data } = await apiClient.get<JobSummary[]>("/jobs", { params });
  return data;
}

export async function fetchJobDetail(jobId: string): Promise<JobDetail> {
  const { data } = await apiClient.get<JobDetail>(`/jobs/${jobId}`);
  return data;
}

export async function rerunJob(jobId: string): Promise<RerunResult> {
  const { data } = await apiClient.post<RerunResult>(`/jobs/${jobId}/rerun`);
  return data;
}

export async function fetchJobStatus(jobId: string): Promise<JobStatusView> {
  const { data } = await apiClient.get<JobStatusView>(`/jobs/${jobId}/status`);
  return data;
}

export async function fetchJobFeedback(jobId: string): Promise<JobFeedback | null> {
  const { data } = await apiClient.get<JobFeedback | null>(`/jobs/${jobId}/feedback`);
  return data;
}

export async function submitJobFeedback(jobId: string, payload: JobFeedbackPayload): Promise<JobFeedback> {
  const { data } = await apiClient.post<JobFeedback>(`/jobs/${jobId}/feedback`, payload);
  return data;
}
