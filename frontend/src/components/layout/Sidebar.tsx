import { FlaskConical, PanelLeftClose } from "lucide-react";
import clsx from "clsx";
import { useUiStore } from "@/store/uiStore";

interface SidebarProps {
  isMobile?: boolean;
}

export function Sidebar({ isMobile = false }: SidebarProps) {
  const { sidebarOpen, toggleSidebar } = useUiStore();

  return (
    <aside
      className={clsx(
        "fixed inset-y-0 left-0 z-40 flex w-72 flex-col overflow-y-auto border-r border-white/10 bg-ink-900/95 px-4 py-5 backdrop-blur-lg transition-transform lg:translate-x-0",
        isMobile ? (sidebarOpen ? "translate-x-0" : "-translate-x-full") : "",
      )}
    >
      <div className="mb-7 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-accent-cyan">TestaCode</p>
          <h1 className="mt-1 flex items-center gap-2 text-lg font-semibold text-white">
            <FlaskConical className="text-accent-magenta" size={18} aria-hidden="true" />
            About
          </h1>
        </div>
        <button className="focus-ring rounded-lg border border-white/10 p-2 lg:hidden" onClick={toggleSidebar}>
          <PanelLeftClose size={15} aria-hidden="true" />
        </button>
      </div>

      <section className="mt-2 flex flex-1 flex-col rounded-xl border border-white/10 bg-ink-800/80 p-4">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-cyan">About TestaCode</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-300">
          TestaCode is an AI-assisted test engineering workspace for generating, evaluating, and iterating tests from
          real source code. It combines prompt guidance, code parsing, model-driven generation, quality scoring, and
          artifact tracking in one flow.
        </p>

        <div className="mt-4 space-y-3">
          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-cyan">Core Workflow</h3>
            <ul className="mt-2 space-y-2 text-sm text-slate-300">
              <li>1. Provide intent in the prompt and paste code or upload a file.</li>
              <li>2. Language is auto-detected and normalized before generation.</li>
              <li>3. Tests are generated with framework-aware structure and edge-case coverage.</li>
              <li>4. Output includes quality score, uncovered areas, and warning signals.</li>
              <li>5. Jobs can be reviewed, rerun, and traced through saved outputs and status updates.</li>
            </ul>
          </div>

        </div>
      </section>
    </aside>
  );
}
