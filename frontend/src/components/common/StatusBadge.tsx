import { AlertTriangle, CheckCircle2, Clock3, Info, XCircle } from "lucide-react";
import clsx from "clsx";
import { statusTone } from "@/utils/format";

interface StatusBadgeProps {
  value?: string | null;
}

const toneClasses = {
  success: "border-accent-green/40 bg-accent-green/10 text-accent-green",
  warning: "border-accent-orange/40 bg-accent-orange/10 text-accent-orange",
  danger: "border-accent-red/40 bg-accent-red/10 text-accent-red",
  info: "border-accent-cyan/40 bg-accent-cyan/10 text-accent-cyan",
  neutral: "border-slate-500/40 bg-slate-500/10 text-slate-300",
};

const toneIcon = {
  success: CheckCircle2,
  warning: Clock3,
  danger: XCircle,
  info: Info,
  neutral: AlertTriangle,
};

export function StatusBadge({ value }: StatusBadgeProps) {
  const tone = statusTone(value);
  const Icon = toneIcon[tone];

  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs font-semibold", toneClasses[tone])}>
      <Icon size={12} aria-hidden="true" />
      <span>{value ?? "unknown"}</span>
    </span>
  );
}
