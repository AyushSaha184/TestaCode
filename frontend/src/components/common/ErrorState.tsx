import { TriangleAlert } from "lucide-react";

interface ErrorStateProps {
  title: string;
  description: string;
  onRetry?: () => void;
}

export function ErrorState({ title, description, onRetry }: ErrorStateProps) {
  return (
    <div className="glass-card flex min-h-44 flex-col items-center justify-center gap-3 p-8 text-center">
      <TriangleAlert className="text-accent-red" size={28} aria-hidden="true" />
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="max-w-md text-sm text-slate-300">{description}</p>
      {onRetry ? (
        <button className="focus-ring rounded-lg bg-accent-red/20 px-3 py-2 text-sm font-medium text-accent-red" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
