import { Inbox } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="glass-card flex min-h-44 flex-col items-center justify-center gap-2 p-8 text-center">
      <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-[#0b1324] text-accent-cyan">
        <Inbox size={22} aria-hidden="true" />
      </span>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="max-w-md text-sm text-slate-400">{description}</p>
    </div>
  );
}
