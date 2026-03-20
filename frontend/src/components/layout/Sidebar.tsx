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
        "fixed inset-y-0 left-0 z-40 w-72 overflow-y-auto border-r border-white/10 bg-ink-900/95 px-4 py-5 backdrop-blur-lg transition-transform lg:translate-x-0",
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

      <section className="mt-2 rounded-xl border border-white/10 bg-ink-800/80 p-4">
        <h2 className="text-sm font-semibold text-white">About TestaCode</h2>
        <p className="mt-2 text-xs leading-relaxed text-slate-300">
          TestaCode is an AI-assisted test engineering workspace for generating, evaluating, and iterating tests from
          real source code. It combines prompt guidance, code parsing, model-driven generation, quality scoring, and
          CI-aware feedback in one flow.
        </p>

        <div className="mt-4 space-y-3">
          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-cyan">Core Workflow</h3>
            <ul className="mt-2 space-y-1.5 text-xs text-slate-300">
              <li>1. Provide intent in the prompt and paste code or upload a file.</li>
              <li>2. Language is auto-detected and normalized before generation.</li>
              <li>3. Tests are generated with framework-aware structure and edge-case coverage.</li>
              <li>4. Output includes job ID, quality score, uncovered areas, and warning signals.</li>
              <li>5. Jobs can be reviewed, rerun, and traced against CI status.</li>
            </ul>
          </div>

          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-magenta">What You Get</h3>
            <ul className="mt-2 space-y-1.5 text-xs text-slate-300">
              <li>Deterministic test artifacts with consistent formatting.</li>
              <li>Unified handling for prompt-only, pasted code, and file-upload inputs.</li>
              <li>Quality diagnostics: score, blind spots, and generation warnings.</li>
              <li>Optional auto-commit workflow for generated tests.</li>
              <li>CI workflow polling for visibility into test pipeline outcomes.</li>
            </ul>
          </div>

          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-blue">Architecture</h3>
            <ul className="mt-2 space-y-1.5 text-xs text-slate-300">
              <li>Frontend: React + Vite + TypeScript + TanStack Query + Zustand.</li>
              <li>Backend: FastAPI orchestration with parser, intent, and generation agents.</li>
              <li>Storage: Supabase Postgres for jobs and generated output metadata.</li>
              <li>Caching: TTL-based cache with optional Redis-backed acceleration.</li>
            </ul>
          </div>

          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-green">Session Behavior</h3>
            <p className="mt-2 text-xs leading-relaxed text-slate-300">
              Each page load creates a fresh client session ID to reduce cross-session mixing and keep request context
              isolated while you iterate on prompts and code.
            </p>
          </div>
        </div>
      </section>
    </aside>
  );
}
