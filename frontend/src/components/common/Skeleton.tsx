import clsx from "clsx";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return <div className={clsx("glass-card animate-pulse rounded-xl bg-[#121b2f]/80", className)} />;
}
