import { TriangleAlert } from "lucide-react";

interface ErrorStateProps {
  title: string;
  description: string;
  onRetry?: () => void;
}

export function ErrorState({ title, description, onRetry }: ErrorStateProps) {
  return (
    <div className="glass-card flex min-h-44 flex-col items-center justify-center gap-3 p-8 text-center">
      <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl border border-accent-red/40 bg-accent-red/10 text-accent-red">
        <TriangleAlert size={22} aria-hidden="true" />
      </span>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="max-w-md text-sm text-slate-400">{description}</p>
      {onRetry ? (
        <button className="focus-ring rounded-xl border border-accent-red/45 bg-accent-red/12 px-3 py-2 text-sm font-medium text-accent-red hover:bg-accent-red/20" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}
