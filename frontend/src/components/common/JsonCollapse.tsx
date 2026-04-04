interface JsonCollapseProps {
  title: string;
  value: Record<string, unknown>;
}

export function JsonCollapse({ title, value }: JsonCollapseProps) {
  return (
    <details className="rounded-xl border border-white/10 bg-[#0a1120]" open={false}>
      <summary className="focus-ring cursor-pointer list-none px-3 py-2 text-sm font-semibold text-slate-100">{title}</summary>
      <pre className="max-h-72 overflow-auto border-t border-white/10 px-3 py-2 text-xs text-slate-200">{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}
