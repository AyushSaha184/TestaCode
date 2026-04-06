import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { RefreshCcw, ThumbsDown, ThumbsUp } from "lucide-react";
import { Card } from "@/components/common/Card";
import { CodeViewer } from "@/components/common/CodeViewer";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { JsonCollapse } from "@/components/common/JsonCollapse";
import { Skeleton } from "@/components/common/Skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useJobDetailQuery, useJobStatusQuery } from "@/hooks/queries/useJobDetailQuery";
import { useJobFeedbackQuery } from "@/hooks/queries/useJobFeedbackQuery";
import { useRerunMutation } from "@/hooks/queries/useRerunMutation";
import type { FeedbackValue } from "@/types/api";
import { formatDate } from "@/utils/format";

interface GenerateReturnState {
  targetJobId?: string;
  prefillPrompt?: string;
  prefillCode?: string;
}

function extractRawCode(classifiedIntent: unknown): string {
  if (!classifiedIntent || typeof classifiedIntent !== "object") {
    return "";
  }
  const rawCode = (classifiedIntent as Record<string, unknown>).raw_code;
  return typeof rawCode === "string" ? rawCode : "";
}

export function JobDetailPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const generateReturnState = (location.state as GenerateReturnState | null) || null;
  const { jobId = "" } = useParams();
  const detailQuery = useJobDetailQuery(jobId);
  const statusQuery = useJobStatusQuery(jobId);
  const rerunMutation = useRerunMutation(jobId);
  const feedbackQuery = useJobFeedbackQuery(jobId);
  const [feedbackValue, setFeedbackValue] = useState<FeedbackValue | null>(null);
  const [correctionText, setCorrectionText] = useState("");

  useEffect(() => {
    if (!feedbackQuery.data) {
      return;
    }
    setFeedbackValue(feedbackQuery.data.feedback_value);
    setCorrectionText(feedbackQuery.data.correction_text || "");
  }, [feedbackQuery.data]);

  if (!jobId) {
    return <EmptyState title="No Job Selected" description="Pick a job from the jobs page to inspect details." />;
  }

  if (detailQuery.isLoading) {
    return (
      <div className="grid gap-3">
        <Skeleton className="h-36" />
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
    );
  }

  if (detailQuery.isError) {
    return <ErrorState title="Unable to load job" description={(detailQuery.error as Error).message} onRetry={() => detailQuery.refetch()} />;
  }

  const detail = detailQuery.data;
  if (!detail) {
    return <EmptyState title="Job not found" description="The requested job does not exist or was deleted." />;
  }

  return (
    <div className="space-y-3 md:space-y-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-white">Detailed Report</h3>
            <p className="text-sm text-slate-400">Created {formatDate(detail.created_at)}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="btn-ghost"
              onClick={() => {
                if (generateReturnState?.targetJobId) {
                  navigate(`/generate?jobId=${generateReturnState.targetJobId}`, {
                    state: {
                      targetJobId: generateReturnState.targetJobId,
                      prefillPrompt: generateReturnState.prefillPrompt,
                      prefillCode: generateReturnState.prefillCode,
                    },
                  });
                  return;
                }

                navigate(`/generate?jobId=${detail.id}`, {
                  state: {
                    targetJobId: detail.id,
                    prefillPrompt: detail.user_prompt,
                    prefillCode: extractRawCode(detail.classified_intent),
                  },
                });
              }}
            >
              Back to output
            </button>
            <StatusBadge value={statusQuery.data?.ci_status || detail.ci_status || detail.status} />
            <button
              disabled={rerunMutation.isPending}
              className="focus-ring inline-flex items-center gap-2 rounded-xl border border-accent-magenta/45 bg-accent-magenta/14 px-3 py-2 text-xs font-semibold text-accent-magenta hover:bg-accent-magenta/20 disabled:opacity-60"
              onClick={async () => {
                try {
                  const response = await rerunMutation.mutateAsync();
                  toast.success("Rerun created");
                  navigate(`/jobs/${response.rerun_job_id}`);
                } catch (error) {
                  toast.error((error as Error).message);
                }
              }}
            >
              <RefreshCcw size={13} className={rerunMutation.isPending ? "animate-spin" : ""} aria-hidden="true" />
              {rerunMutation.isPending ? "Rerunning..." : "Rerun"}
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 text-sm md:grid-cols-2 xl:grid-cols-4">
          <InfoItem label="Input mode" value={detail.input_mode} />
          <InfoItem label="Language" value={detail.detected_language} />
          <InfoItem label="Status" value={detail.status} />
          <InfoItem label="Framework" value={detail.framework_used || "-"} />
          <InfoItem label="Filename" value={detail.original_filename || "-"} />
          <InfoItem label="Commit SHA" value={detail.commit_sha || "-"} mono />
          <InfoItem label="Status updated" value={formatDate(detail.ci_updated_at)} />
        </div>
      </Card>

      <Card className="space-y-3">
        <h4 className="font-semibold text-white">Classified Intent</h4>
        <JsonCollapse title="View intent JSON" value={detail.classified_intent} />
      </Card>

      <Card className="space-y-3">
        <h4 className="font-semibold text-white">Analysis</h4>
        <pre className="whitespace-pre-wrap rounded-xl border border-white/10 bg-[#0b1324] p-3 text-sm text-slate-200">
          {detail.analysis_text || "No analysis text"}
        </pre>
      </Card>

      <Card className="space-y-3">
        <h4 className="font-semibold text-white">Generated Test Code</h4>
        <div className="overflow-hidden rounded-xl border border-white/10">
          <CodeViewer code={detail.generated_test_code || ""} language={detail.detected_language} />
        </div>
      </Card>

      <div className="grid gap-3 md:grid-cols-2">
        <Card>
          <h4 className="mb-2 font-semibold text-white">Warnings</h4>
          <div className="flex flex-wrap gap-2">
            {detail.warnings.length ? (
              detail.warnings.map((item) => (
                <span key={item} className="tag-red">
                  {item}
                </span>
              ))
            ) : (
              <span className="text-sm text-slate-400">None</span>
            )}
          </div>
        </Card>

        <Card>
          <h4 className="mb-2 font-semibold text-white">Uncovered Areas</h4>
          <div className="flex flex-wrap gap-2">
            {detail.uncovered_areas.length ? (
              detail.uncovered_areas.map((item) => (
                <span key={item} className="tag-orange">
                  {item}
                </span>
              ))
            ) : (
              <span className="text-sm text-slate-400">None</span>
            )}
          </div>
        </Card>
      </div>

      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h4 className="font-semibold text-white">Human Feedback</h4>
          {feedbackQuery.data ? (
            <span className="tag-green">
              Saved {formatDate(feedbackQuery.data.updated_at)}
            </span>
          ) : (
            <span className="tag-neutral">Not reviewed</span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setFeedbackValue("up")}
            className={`focus-ring rounded-lg border px-3 py-2 text-sm font-medium ${
              feedbackValue === "up"
                ? "border-accent-green/60 bg-accent-green/20 text-accent-green"
                : "border-white/20 bg-[#0a1120] text-slate-200"
            }`}
          >
            <span className="inline-flex items-center gap-2">
              <ThumbsUp size={14} aria-hidden="true" />
            Thumbs up
            </span>
          </button>
          <button
            type="button"
            onClick={() => setFeedbackValue("down")}
            className={`focus-ring rounded-lg border px-3 py-2 text-sm font-medium ${
              feedbackValue === "down"
                ? "border-accent-red/60 bg-accent-red/20 text-accent-red"
                : "border-white/20 bg-[#0a1120] text-slate-200"
            }`}
          >
            <span className="inline-flex items-center gap-2">
              <ThumbsDown size={14} aria-hidden="true" />
            Thumbs down
            </span>
          </button>
        </div>

        <div className="grid gap-3">
          <label className="grid gap-2">
            <span className="text-xs text-slate-400">Correction / suggestion</span>
            <textarea
              value={correctionText}
              onChange={(event) => setCorrectionText(event.target.value)}
              rows={8}
              className="input-base min-h-32"
              placeholder="Optional: suggest exact test improvements or missing cases"
            />
          </label>
        </div>
      </Card>

      <Card>
        <h4 className="mb-2 font-semibold text-white">Latest Run</h4>
        {detail.latest_run ? (
          <div className="grid gap-2 text-sm md:grid-cols-2 xl:grid-cols-5">
            <InfoItem label="Pass" value={String(detail.latest_run.pass_count)} />
            <InfoItem label="Fail" value={String(detail.latest_run.fail_count)} />
            <InfoItem label="Error" value={String(detail.latest_run.error_count)} />
            <InfoItem label="Coverage" value={`${detail.latest_run.coverage_percentage}%`} />
            <InfoItem label="Run URL" value={detail.latest_run.ci_run_url || "-"} />
          </div>
        ) : (
          <p className="text-sm text-slate-400">No test run stats available.</p>
        )}
      </Card>

    </div>
  );
}

function InfoItem({
  label,
  value,
  mono = false,
  accent,
}: {
  label: string;
  value: string;
  mono?: boolean;
  accent?: "cyan";
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-[#0a1120] p-3">
      <p className="section-label">{label}</p>
      <p className={`mt-1 text-sm ${accent === "cyan" ? "text-accent-cyan" : "text-slate-100"} ${mono ? "font-code" : ""}`}>{value}</p>
    </div>
  );
}
