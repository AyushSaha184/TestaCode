import { useMemo } from "react";
import { Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/common/Card";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Skeleton } from "@/components/common/Skeleton";
import { useJobsQuery } from "@/hooks/queries/useJobsQuery";

const pieColors = ["#1BC5FF", "#33E9A5", "#FFAE57", "#FF6B7A", "#D44CFF"];
const tooltipStyle = {
  backgroundColor: "#0d1117",
  border: "1px solid rgba(255,255,255,0.07)",
  borderRadius: "10px",
};

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
      <div className="grid gap-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
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
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="space-y-1" elevated>
          <p className="section-label">Total Jobs</p>
          <p className="text-3xl font-bold text-accent-cyan">{jobsQuery.data.length}</p>
        </Card>
        <Card className="space-y-1" elevated>
          <p className="section-label">Avg Quality</p>
          <p className="text-3xl font-bold text-accent-magenta">{stats.avgQuality}</p>
        </Card>
        <Card className="space-y-1" elevated>
          <p className="section-label">Languages</p>
          <p className="text-3xl font-bold text-accent-green">{stats.languageData.length}</p>
        </Card>
        <Card className="space-y-1" elevated>
          <p className="section-label">Statuses</p>
          <p className="text-3xl font-bold text-accent-orange">{stats.statusData.length}</p>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-lg font-semibold">Status Distribution</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={stats.statusData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={92}>
                  {stats.statusData.map((entry, idx) => (
                    <Cell key={entry.name} fill={pieColors[idx % pieColors.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex flex-wrap gap-3">
            {stats.statusData.map((entry, idx) => (
              <span key={entry.name} className="inline-flex items-center gap-2 text-xs text-slate-300">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: pieColors[idx % pieColors.length] }} />
                {entry.name}
              </span>
            ))}
          </div>
        </Card>

        <Card>
          <h3 className="mb-3 text-lg font-semibold">Quality Score Trend</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats.trend}>
                <XAxis dataKey="name" stroke="#7f8ca6" tickLine={false} axisLine={{ stroke: "rgba(255,255,255,0.08)" }} />
                <YAxis stroke="#7f8ca6" tickLine={false} axisLine={{ stroke: "rgba(255,255,255,0.08)" }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="quality" stroke="#4F7CFF" strokeWidth={2.4} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card>
        <h3 className="mb-3 text-lg font-semibold">Language Distribution</h3>
        <div className="space-y-3">
          {stats.languageData.map((item, idx) => {
            const maxValue = Math.max(...stats.languageData.map((entry) => entry.value), 1);
            const width = (item.value / maxValue) * 100;
            return (
              <div key={item.name}>
                <div className="mb-1 flex items-center justify-between text-sm text-slate-300">
                  <span className="capitalize">{item.name}</span>
                  <span>{item.value}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-white/8">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${width}%`, backgroundColor: pieColors[idx % pieColors.length] }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
