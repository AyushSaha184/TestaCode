import { Inbox } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="glass-card flex min-h-44 flex-col items-center justify-center gap-2 p-8 text-center">
      <Inbox className="text-accent-cyan" size={28} aria-hidden="true" />
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="max-w-md text-sm text-slate-300">{description}</p>
    </div>
  );
}
