import { useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { Card } from "@/components/common/Card";
import { CodeViewer } from "@/components/common/CodeViewer";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { JsonCollapse } from "@/components/common/JsonCollapse";
import { Skeleton } from "@/components/common/Skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useJobDetailQuery, useJobStatusQuery } from "@/hooks/queries/useJobDetailQuery";
import { usePollCiMutation, useRerunMutation } from "@/hooks/queries/useRerunMutation";
import { formatDate } from "@/utils/format";

export function JobDetailPage() {
  const { jobId = "" } = useParams();
  const detailQuery = useJobDetailQuery(jobId);
  const statusQuery = useJobStatusQuery(jobId);
  const rerunMutation = useRerunMutation(jobId);
  const pollMutation = usePollCiMutation(jobId);

  if (!jobId) {
    return <EmptyState title="No Job Selected" description="Pick a job from the jobs page to inspect details." />;
  }

  if (detailQuery.isLoading) {
    return (
      <div className="grid gap-3">
        <Skeleton className="h-24" />
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
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-white">Job {detail.id}</h3>
            <p className="text-sm text-slate-400">Created {formatDate(detail.created_at)}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge value={statusQuery.data?.ci_status || detail.ci_status || detail.status} />
            <button
              className="focus-ring rounded-lg border border-accent-cyan/40 bg-accent-cyan/10 px-3 py-2 text-xs font-semibold text-accent-cyan"
              onClick={async () => {
                try {
                  await pollMutation.mutateAsync();
                  toast.success("CI status refreshed");
                } catch (error) {
                  toast.error((error as Error).message);
                }
              }}
            >
              Poll CI
            </button>
            <button
              className="focus-ring rounded-lg border border-accent-magenta/40 bg-accent-magenta/15 px-3 py-2 text-xs font-semibold text-accent-magenta"
              onClick={async () => {
                try {
                  const response = await rerunMutation.mutateAsync();
                  toast.success(`Rerun created: ${response.rerun_job_id}`);
                } catch (error) {
                  toast.error((error as Error).message);
                }
              }}
            >
              Rerun
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 text-sm md:grid-cols-2 xl:grid-cols-4">
          <InfoItem label="Input mode" value={detail.input_mode} />
          <InfoItem label="Language" value={detail.detected_language} />
          <InfoItem label="Status" value={detail.status} />
          <InfoItem label="Framework" value={detail.framework_used || "-"} />
          <InfoItem label="Filename" value={detail.original_filename || "-"} />
          <InfoItem label="Quality score" value={detail.quality_score?.toString() || "-"} />
          <InfoItem label="Commit SHA" value={detail.commit_sha || "-"} mono />
          <InfoItem label="CI updated" value={formatDate(detail.ci_updated_at)} />
        </div>
      </Card>

      <Card className="space-y-3">
        <h4 className="font-semibold text-white">Classified Intent</h4>
        <JsonCollapse title="View intent JSON" value={detail.classified_intent} />
      </Card>

      <Card className="space-y-3">
        <h4 className="font-semibold text-white">Analysis</h4>
        <pre className="whitespace-pre-wrap rounded-lg border border-white/10 bg-ink-900/70 p-3 text-sm text-slate-200">
          {detail.analysis_text || "No analysis text"}
        </pre>
      </Card>

      <Card className="space-y-3">
        <h4 className="font-semibold text-white">Generated Test Code</h4>
        <div className="overflow-hidden rounded-lg border border-white/10">
          <CodeViewer code={detail.generated_test_code || ""} language={detail.detected_language} />
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <h4 className="mb-2 font-semibold text-white">Warnings</h4>
          <div className="flex flex-wrap gap-2">
            {detail.warnings.length ? (
              detail.warnings.map((item) => (
                <span key={item} className="rounded-full border border-accent-red/40 bg-accent-red/10 px-2 py-1 text-xs text-accent-red">
                  {item}
                </span>
              ))
            ) : (
              <span className="text-sm text-slate-400">No warnings</span>
            )}
          </div>
        </Card>

        <Card>
          <h4 className="mb-2 font-semibold text-white">Uncovered Areas</h4>
          <div className="flex flex-wrap gap-2">
            {detail.uncovered_areas.length ? (
              detail.uncovered_areas.map((item) => (
                <span key={item} className="rounded-full border border-accent-orange/40 bg-accent-orange/10 px-2 py-1 text-xs text-accent-orange">
                  {item}
                </span>
              ))
            ) : (
              <span className="text-sm text-slate-400">No uncovered areas</span>
            )}
          </div>
        </Card>
      </div>

      <Card>
        <h4 className="mb-2 font-semibold text-white">Latest Run</h4>
        {detail.latest_run ? (
          <div className="grid gap-2 text-sm md:grid-cols-2 xl:grid-cols-5">
            <InfoItem label="Pass" value={String(detail.latest_run.pass_count)} />
            <InfoItem label="Fail" value={String(detail.latest_run.fail_count)} />
            <InfoItem label="Error" value={String(detail.latest_run.error_count)} />
            <InfoItem label="Coverage" value={`${detail.latest_run.coverage_percentage}%`} />
            <InfoItem label="CI URL" value={detail.latest_run.ci_run_url || "-"} />
          </div>
        ) : (
          <p className="text-sm text-slate-400">No test run stats available.</p>
        )}
      </Card>

      <Card>
        <h4 className="mb-2 font-semibold text-white">Artifacts</h4>
        <div className="grid gap-2 text-sm md:grid-cols-2">
          <InfoItem label="Test path" value={detail.output_test_path || "-"} mono />
          <InfoItem label="Metadata path" value={detail.output_metadata_path || "-"} mono />
          <InfoItem label="Test URL" value={detail.output_test_url || "-"} />
          <InfoItem label="Metadata URL" value={detail.output_metadata_url || "-"} />
        </div>
      </Card>
    </div>
  );
}

function InfoItem({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-lg border border-white/10 bg-ink-900/70 p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`mt-1 text-sm text-slate-100 ${mono ? "font-mono" : ""}`}>{value}</p>
    </div>
  );
}
