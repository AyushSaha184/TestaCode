import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/common/Card";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Skeleton } from "@/components/common/Skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useJobsQuery } from "@/hooks/queries/useJobsQuery";
import { useUiStore } from "@/store/uiStore";
import { formatDate, shortId } from "@/utils/format";

export function JobsPage() {
  const navigate = useNavigate();
  const { statusFilter, languageFilter, searchText, setFilters, setSelectedJobId } = useUiStore();
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const query = useJobsQuery(page, pageSize);

  const filtered = useMemo(() => {
    const jobs = query.data || [];
    return jobs.filter((job) => {
      const matchesStatus = statusFilter === "all" || job.status === statusFilter;
      const matchesLang = languageFilter === "all" || job.detected_language === languageFilter;
      const text = searchText.toLowerCase();
      const matchesText =
        !text ||
        job.id.toLowerCase().includes(text) ||
        (job.framework_used || "").toLowerCase().includes(text) ||
        job.detected_language.toLowerCase().includes(text);
      return matchesStatus && matchesLang && matchesText;
    });
  }, [languageFilter, query.data, searchText, statusFilter]);

  if (query.isLoading) {
    return (
      <div className="grid gap-3">
        <Skeleton className="h-12" />
        <Skeleton className="h-80" />
      </div>
    );
  }

  if (query.isError) {
    return <ErrorState title="Unable to load jobs" description={(query.error as Error).message} onRetry={() => query.refetch()} />;
  }

  return (
    <div className="space-y-4">
      <Card className="grid gap-3 md:grid-cols-4">
        <select className="focus-ring rounded-lg border border-white/10 bg-ink-900 px-3 py-2 text-sm" value={statusFilter} onChange={(e) => setFilters({ statusFilter: e.target.value })}>
          <option value="all">All status</option>
          <option value="queued">Queued</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>

        <select className="focus-ring rounded-lg border border-white/10 bg-ink-900 px-3 py-2 text-sm" value={languageFilter} onChange={(e) => setFilters({ languageFilter: e.target.value })}>
          <option value="all">All languages</option>
          <option value="python">Python</option>
          <option value="javascript">JavaScript</option>
          <option value="typescript">TypeScript</option>
          <option value="java">Java</option>
        </select>

        <button className="focus-ring rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm" onClick={() => query.refetch()}>
          Refresh List
        </button>
      </Card>

      {filtered.length === 0 ? (
        <EmptyState title="No jobs match filters" description="Try clearing filters or generating a new job." />
      ) : (
        <Card className="overflow-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wide text-slate-400">
                <th className="px-2 py-2">Job</th>
                <th className="px-2 py-2">Created</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Language</th>
                <th className="px-2 py-2">Quality</th>
                <th className="px-2 py-2">Framework</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((job) => (
                <tr
                  key={job.id}
                  className="cursor-pointer border-t border-white/5 hover:bg-white/5"
                  onClick={() => {
                    setSelectedJobId(job.id);
                    navigate(`/jobs/${job.id}`);
                  }}
                >
                  <td className="px-2 py-3 font-mono text-xs text-slate-200" title={job.id}>
                    {shortId(job.id)}
                  </td>
                  <td className="px-2 py-3 text-slate-300">{formatDate(job.created_at)}</td>
                  <td className="px-2 py-3">
                    <StatusBadge value={job.status} />
                  </td>
                  <td className="px-2 py-3 capitalize text-slate-200">{job.detected_language}</td>
                  <td className="px-2 py-3 text-slate-200">{job.quality_score ?? "-"}</td>
                  <td className="px-2 py-3 text-slate-300">{job.framework_used ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
            <span>Page {page}</span>
            <div className="space-x-2">
              <button className="focus-ring rounded border border-white/20 px-2 py-1 disabled:opacity-40" disabled={page <= 1} onClick={() => setPage((prev) => prev - 1)}>
                Prev
              </button>
              <button className="focus-ring rounded border border-white/20 px-2 py-1 disabled:opacity-40" disabled={(query.data?.length ?? 0) < pageSize} onClick={() => setPage((prev) => prev + 1)}>
                Next
              </button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
