import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  Activity,
  ChevronDown,
  ChevronUp,
  FlaskConical,
  History,
  PanelLeftClose,
  Sparkles,
  CircleHelp,
} from "lucide-react";
import clsx from "clsx";
import { useUiStore } from "@/store/uiStore";

interface SidebarProps {
  isMobile?: boolean;
}

export function Sidebar({ isMobile = false }: SidebarProps) {
  const { sidebarOpen, toggleSidebar } = useUiStore();
  const [aboutExpanded, setAboutExpanded] = useState(false);

  const navItems = [
    {
      to: "/generate",
      label: "Generate",
      description: "Build tests from code",
      icon: Sparkles,
    },
    {
      to: "/jobs",
      label: "Output History",
      description: "Review past outputs",
      icon: History,
    },
    {
      to: "/analytics",
      label: "Analytics",
      description: "Quality & trends",
      icon: Activity,
    },
  ];

  return (
    <aside
      className={clsx(
        "fixed inset-y-0 left-0 z-40 flex w-56 flex-col overflow-y-auto border-r border-[rgba(255,255,255,0.06)] bg-[#060910] px-3 py-5 backdrop-blur-lg transition-transform lg:translate-x-0",
        isMobile ? (sidebarOpen ? "translate-x-0" : "-translate-x-full") : "",
      )}
    >
      <div className="mb-6 flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-accent-blue to-accent-magenta shadow-glow">
            <FlaskConical className="text-white" size={16} aria-hidden="true" />
          </span>
          <h1 className="text-2xl font-semibold leading-none text-white">TestaCode</h1>
        </div>
        <button className="focus-ring rounded-lg border border-white/10 p-2 lg:hidden" onClick={toggleSidebar}>
          <PanelLeftClose size={15} aria-hidden="true" />
        </button>
      </div>

      <p className="section-label px-2">Menu</p>

      <nav className="mt-3 flex flex-1 flex-col gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  "group relative rounded-xl px-3 py-2 transition",
                  isActive ? "bg-[rgba(255,255,255,0.07)]" : "hover:bg-[rgba(255,255,255,0.04)]",
                )
              }
              onClick={() => {
                if (isMobile) {
                  toggleSidebar();
                }
              }}
            >
              {({ isActive }) => (
                <>
                  <span
                    className={clsx(
                      "absolute inset-y-1 left-0 w-[2px] rounded-full bg-gradient-to-b from-accent-blue to-accent-magenta",
                      isActive ? "opacity-100" : "opacity-0 group-hover:opacity-60",
                    )}
                  />
                  <div className="flex items-start gap-2">
                    <Icon size={16} className={clsx("mt-0.5", isActive ? "text-accent-blue" : "text-slate-500")} aria-hidden="true" />
                    <div>
                      <p className={clsx("text-base font-medium leading-tight", isActive ? "text-white" : "text-[#64748b]")}>{item.label}</p>
                      <p className="text-xs leading-tight text-slate-500">{item.description}</p>
                    </div>
                  </div>
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="mt-auto border-t border-white/10 pt-3">
        <button
          type="button"
          className="focus-ring flex w-full items-center justify-between rounded-xl px-2 py-2 text-left hover:bg-white/5"
          onClick={() => setAboutExpanded((previous) => !previous)}
          aria-expanded={aboutExpanded}
        >
          <div className="flex items-start gap-2">
            <CircleHelp className="mt-0.5 text-slate-400" size={16} aria-hidden="true" />
            <div>
              <p className="text-base font-medium leading-tight text-slate-300">About TestaCode</p>
              <p className="text-xs leading-tight text-slate-500">How it works</p>
            </div>
          </div>
          {aboutExpanded ? <ChevronUp size={14} className="text-slate-400" /> : <ChevronDown size={14} className="text-slate-400" />}
        </button>

        {aboutExpanded ? (
          <section className="glass-card mt-2 space-y-2 p-2.5 text-xs leading-relaxed text-slate-300">
            <p>
              TestaCode is an AI-assisted test engineering workspace for generating, evaluating, and iterating tests from
              real source code. It combines prompt guidance, code parsing, model-driven generation, quality scoring, and
              artifact tracking in one flow.
            </p>
            <div>
              <p className="section-label mb-1">Core Workflow</p>
              <ul className="space-y-1 text-xs text-slate-300">
                <li>1. Provide intent in the prompt and paste code or upload a file.</li>
                <li>2. Language is auto-detected and normalized before generation.</li>
                <li>3. Tests are generated with framework-aware structure and edge-case coverage.</li>
                <li>4. Output includes quality score, uncovered areas, and warning signals.</li>
                <li>5. Jobs can be reviewed, rerun, and traced through saved outputs and status updates.</li>
              </ul>
            </div>
          </section>
        ) : null}
      </div>
    </aside>
  );
}
