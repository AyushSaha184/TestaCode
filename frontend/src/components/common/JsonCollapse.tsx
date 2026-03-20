import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

interface JsonCollapseProps {
  title: string;
  value: Record<string, unknown>;
}

export function JsonCollapse({ title, value }: JsonCollapseProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-xl border border-white/10 bg-ink-900/70">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="focus-ring flex w-full items-center justify-between px-3 py-2 text-left text-sm font-semibold"
      >
        <span>{title}</span>
        {open ? <ChevronDown size={16} aria-hidden="true" /> : <ChevronRight size={16} aria-hidden="true" />}
      </button>
      {open ? (
        <pre className="max-h-72 overflow-auto border-t border-white/10 px-3 py-2 text-xs text-slate-200">{JSON.stringify(value, null, 2)}</pre>
      ) : null}
    </div>
  );
}
