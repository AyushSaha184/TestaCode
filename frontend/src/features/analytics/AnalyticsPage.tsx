import { useMemo } from "react";
import { Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/common/Card";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Skeleton } from "@/components/common/Skeleton";
import { useJobsQuery } from "@/hooks/queries/useJobsQuery";

const pieColors = ["#1BC5FF", "#33E9A5", "#FFAE57", "#FF6B7A", "#D44CFF"];

export function AnalyticsPage() {
  const jobsQuery = useJobsQuery(1, 100);

  const stats = useMemo(() => {
    const jobs = jobsQuery.data || [];
    const statusMap = new Map<string, number>();
    const langMap = new Map<string, number>();

    let qualityTotal = 0;
    let qualityCount = 0;

    const trend = jobs
      .slice()
      .reverse()
      .map((job, index) => {
        statusMap.set(job.status, (statusMap.get(job.status) || 0) + 1);
        langMap.set(job.detected_language, (langMap.get(job.detected_language) || 0) + 1);
        if (typeof job.quality_score === "number") {
          qualityTotal += job.quality_score;
          qualityCount += 1;
        }
        return {
          name: `#${index + 1}`,
          quality: job.quality_score ?? 0,
        };
      });

    return {
      avgQuality: qualityCount ? (qualityTotal / qualityCount).toFixed(2) : "0.00",
      statusData: Array.from(statusMap.entries()).map(([name, value]) => ({ name, value })),
      languageData: Array.from(langMap.entries()).map(([name, value]) => ({ name, value })),
      trend,
    };
  }, [jobsQuery.data]);

  if (jobsQuery.isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
    );
  }

  if (jobsQuery.isError) {
    return <ErrorState title="Unable to load analytics" description={(jobsQuery.error as Error).message} onRetry={() => jobsQuery.refetch()} />;
  }

  if (!jobsQuery.data?.length) {
    return <EmptyState title="No data yet" description="Generate test jobs to unlock dashboard analytics." />;
  }

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card>
        <h3 className="mb-3 text-lg font-semibold">Status Distribution</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={stats.statusData} dataKey="value" nameKey="name" innerRadius={65} outerRadius={95}>
                {stats.statusData.map((entry, idx) => (
                  <Cell key={entry.name} fill={pieColors[idx % pieColors.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card>
        <h3 className="mb-3 text-lg font-semibold">Average Quality Score</h3>
        <p className="text-5xl font-bold text-accent-cyan">{stats.avgQuality}</p>
        <p className="mt-2 text-sm text-slate-400">Across latest 100 jobs</p>
      </Card>

      <Card>
        <h3 className="mb-3 text-lg font-semibold">Language Distribution</h3>
        <div className="space-y-2">
          {stats.languageData.map((item, idx) => (
            <div key={item.name} className="flex items-center justify-between rounded-lg border border-white/10 bg-ink-900/70 p-2 text-sm">
              <span className="capitalize">{item.name}</span>
              <span style={{ color: pieColors[idx % pieColors.length] }}>{item.value}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h3 className="mb-3 text-lg font-semibold">Recent Job Trend</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={stats.trend}>
              <XAxis dataKey="name" stroke="#94A3B8" />
              <YAxis stroke="#94A3B8" />
              <Tooltip />
              <Line type="monotone" dataKey="quality" stroke="#1BC5FF" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
