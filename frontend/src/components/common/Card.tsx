import type { PropsWithChildren } from "react";
import clsx from "clsx";

interface CardProps extends PropsWithChildren {
  className?: string;
  elevated?: boolean;
}

export function Card({ className, children, elevated = false }: CardProps) {
  return <section className={clsx(elevated ? "glass-card-elevated" : "glass-card", "p-4 md:p-5", className)}>{children}</section>;
}
