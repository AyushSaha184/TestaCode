export function shortId(value: string): string {
  return value.length > 14 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

export function formatDate(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function statusTone(status: string | null | undefined):
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "neutral" {
  if (!status) return "neutral";
  if (["completed", "ci_passed", "success", "file_written", "committed"].includes(status)) return "success";
  if (["failed", "ci_failed", "cancelled", "timed_out"].includes(status)) return "danger";
  if (["processing", "queued", "ci_running", "ci_pending"].includes(status)) return "warning";
  if (["not_triggered", "ci_unavailable"].includes(status)) return "info";
  return "neutral";
}
