export type InputMode = "paste" | "upload";
export type Language = "python" | "javascript" | "typescript" | "java";
export type JobStatus = "queued" | "processing" | "completed" | "failed";

export interface GenerationResponse {
  job_id: string;
  generated_test_code: string;
  quality_score: number;
  uncovered_areas: string[];
  warnings: string[];
  framework_used: string;
  output_test_path?: string | null;
  output_metadata_path?: string | null;
  output_test_url?: string | null;
  output_metadata_url?: string | null;
  commit_sha?: string | null;
  ci_status?: string | null;
  ci_conclusion?: string | null;
  ci_run_url?: string | null;
  ci_run_id?: string | null;
}

export interface JobSummary {
  id: string;
  created_at: string;
  status: JobStatus;
  detected_language: Language;
  quality_score: number | null;
  framework_used: string | null;
  ci_status?: string | null;
}

export interface TestRunResult {
  pass_count: number;
  fail_count: number;
  error_count: number;
  coverage_percentage: number;
  ci_run_url?: string | null;
  raw_results?: Record<string, unknown> | null;
}

export interface JobDetail {
  id: string;
  created_at: string;
  input_mode: InputMode;
  original_filename?: string | null;
  detected_language: Language;
  user_prompt: string;
  classified_intent: Record<string, unknown>;
  analysis_text?: string | null;
  generated_test_code?: string | null;
  quality_score?: number | null;
  status: JobStatus;
  framework_used?: string | null;
  warnings: string[];
  uncovered_areas: string[];
  output_test_path?: string | null;
  output_metadata_path?: string | null;
  output_test_url?: string | null;
  output_metadata_url?: string | null;
  auto_commit_enabled?: boolean;
  commit_sha?: string | null;
  workflow_name?: string | null;
  ci_status?: string | null;
  ci_conclusion?: string | null;
  ci_run_url?: string | null;
  ci_run_id?: string | null;
  ci_updated_at?: string | null;
  latest_run?: TestRunResult | null;
}

export interface RerunResult {
  original_job_id: string;
  rerun_job_id: string;
  status: JobStatus;
  quality_score?: number | null;
  ci_status?: string | null;
  commit_sha?: string | null;
}

export interface JobStatusView {
  job_id: string;
  status: JobStatus;
  ci_status?: string | null;
  ci_conclusion?: string | null;
  ci_run_url?: string | null;
  ci_run_id?: string | null;
  ci_updated_at?: string | null;
}

export interface JobsQueryParams {
  page: number;
  page_size: number;
}

export interface GeneratePayload {
  input_mode: InputMode;
  user_prompt: string;
  code_content?: string;
  filename?: string;
  language?: Language;
  upload_file?: File;
  auto_commit_enabled?: boolean;
}
