import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { AnalyticsPage } from "@/features/analytics/AnalyticsPage";
import { GeneratePage } from "@/features/generate/GeneratePage";
import { JobDetailPage } from "@/features/job-detail/JobDetailPage";
import { JobsPage } from "@/features/jobs/JobsPage";
import { SettingsPage } from "@/features/settings/SettingsPage";

function AppShell() {
  const location = useLocation();

  const pageMeta = {
    "/generate": { title: "Generate", subtitle: "Build tests from code or uploads" },
    "/jobs": { title: "Job History", subtitle: "Search and review generated test jobs" },
    "/analytics": { title: "Analytics", subtitle: "Quality and execution trends" },
    "/settings": { title: "Settings", subtitle: "Runtime preferences" },
  };

  const meta =
    pageMeta[location.pathname as keyof typeof pageMeta] ||
    (location.pathname.startsWith("/jobs/")
      ? { title: "Job Detail", subtitle: "Inspect generated artifacts and rerun" }
      : { title: "Dashboard", subtitle: "AI test generation control deck" });

  return (
    <DashboardLayout title={meta.title} subtitle={meta.subtitle}>
      <Routes>
        <Route path="/" element={<Navigate to="/generate" replace />} />
        <Route path="/generate" element={<GeneratePage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </DashboardLayout>
  );
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
