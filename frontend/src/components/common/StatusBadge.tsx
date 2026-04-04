import { AlertTriangle, CheckCircle2, Clock3, Info, XCircle } from "lucide-react";
import clsx from "clsx";
import { statusTone } from "@/utils/format";

interface StatusBadgeProps {
  value?: string | null;
}

const toneClasses = {
  success: "border-accent-green/45 bg-accent-green/12 text-accent-green",
  warning: "border-accent-orange/45 bg-accent-orange/12 text-accent-orange",
  danger: "border-accent-red/45 bg-accent-red/12 text-accent-red",
  info: "border-accent-blue/45 bg-accent-blue/12 text-accent-blue",
  neutral: "border-white/20 bg-white/5 text-slate-300",
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
    <span className={clsx("inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-xs font-semibold", toneClasses[tone])}>
      <Icon size={12} aria-hidden="true" />
      <span>{value ?? "unknown"}</span>
    </span>
  );
}
