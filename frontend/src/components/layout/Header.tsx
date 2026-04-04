import { useState } from "react";
import { ChevronDown, Eraser, Menu } from "lucide-react";
import { useIsMutating } from "@tanstack/react-query";
import { useUiStore } from "@/store/uiStore";
import { Bug } from "lucide-react";

interface HeaderProps {
  title: string;
  subtitle: string;
}

const CLEAR_FORM_EVENT = "testacode:clear-generate-form";

export function Header({ title, subtitle }: HeaderProps) {
  const { toggleSidebar } = useUiStore();
  const activeGenerateMutations = useIsMutating({ mutationKey: ["generate-tests"] });
  const isGenerating = activeGenerateMutations > 0;
  const [reportOpen, setReportOpen] = useState(false);

  const onClear = () => {
    if (isGenerating) {
      return;
    }
    window.dispatchEvent(new CustomEvent(CLEAR_FORM_EVENT));
  };

  const reportHref =
    "mailto:ayushsaha184@gmail.com?subject=TestaCode%20Bug%20Report&body=Please%20describe%20the%20bug%20and%20attach%20screenshots.";

  return (
    <header className="sticky top-0 z-20 mb-4 border-b border-[rgba(255,255,255,0.06)] bg-[rgba(6,9,16,0.9)] px-3 py-3 backdrop-blur-[20px] md:px-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <button className="focus-ring rounded-lg border border-white/10 p-2 lg:hidden" onClick={toggleSidebar}>
            <Menu size={16} aria-hidden="true" />
          </button>
          <div>
            <h2 className="text-base font-semibold text-white">{title}</h2>
            <p className="text-xs text-slate-400">{subtitle}</p>
          </div>
        </div>

        <div className="relative flex flex-1 items-center justify-end gap-2 md:max-w-3xl">
          <button
            className="btn-ghost"
            onClick={onClear}
            disabled={isGenerating}
            aria-disabled={isGenerating}
            title={isGenerating ? "Clear is disabled while tests are generating" : "Clear form inputs"}
          >
            <Eraser size={14} aria-hidden="true" />
            Clear
          </button>

          <button
            className="btn-ghost"
            onClick={() => setReportOpen((prev) => !prev)}
            aria-expanded={reportOpen}
            aria-controls="report-bug-dropdown"
          >
            <Bug size={14} />
            Report Bug
            <ChevronDown size={14} aria-hidden="true" className={reportOpen ? "rotate-180 text-slate-200 transition-transform" : "text-slate-400 transition-transform"} />
          </button>

          {reportOpen ? (
            <div
              id="report-bug-dropdown"
              className="glass-card absolute right-0 top-full z-30 mt-2 w-[310px] p-3 text-sm text-slate-300"
            >
              Please report the bug <a href={reportHref} className="text-accent-cyan underline underline-offset-4">here</a> with screenshots.
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
