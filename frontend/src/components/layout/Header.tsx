import { useState } from "react";
import { ChevronDown, Eraser, Menu } from "lucide-react";
import { useIsMutating } from "@tanstack/react-query";
import { useUiStore } from "@/store/uiStore";

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
    <header className="sticky top-0 z-20 mb-4 border-b border-white/10 bg-ink-950/80 px-3 py-3 backdrop-blur md:px-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <button className="focus-ring rounded-lg border border-white/10 p-2 lg:hidden" onClick={toggleSidebar}>
            <Menu size={16} aria-hidden="true" />
          </button>
          <div>
            <h2 className="text-lg font-semibold text-white md:text-xl">{title}</h2>
            <p className="text-xs text-slate-400 md:text-sm">{subtitle}</p>
          </div>
        </div>

        <div className="relative flex flex-1 items-center justify-end gap-2 md:max-w-3xl">
          <button
            className="focus-ring inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm font-medium text-slate-100 hover:bg-white/10"
            onClick={onClear}
            disabled={isGenerating}
            aria-disabled={isGenerating}
            title={isGenerating ? "Clear is disabled while tests are generating" : "Clear form inputs"}
          >
            <Eraser size={14} aria-hidden="true" />
            Clear
          </button>

          <button
            className="focus-ring inline-flex items-center gap-1 rounded-lg border border-[#7a4fff]/45 bg-gradient-to-r from-[#2f1f57]/80 to-[#1f1440]/85 px-3 py-2 text-sm font-medium text-slate-100 shadow-[0_0_0_1px_rgba(122,79,255,0.15)] hover:border-[#9f77ff]/60"
            onClick={() => setReportOpen((prev) => !prev)}
            aria-expanded={reportOpen}
            aria-controls="report-bug-dropdown"
          >
            Report Bug
            <ChevronDown size={14} aria-hidden="true" className={reportOpen ? "rotate-180 transition-transform" : "transition-transform"} />
          </button>

          {reportOpen ? (
            <div
              id="report-bug-dropdown"
              className="absolute right-0 top-full z-30 mt-2 w-[320px] rounded-xl border border-[#7a4fff]/45 bg-gradient-to-r from-[#2f1f57]/95 to-[#1f1440]/95 px-3 py-2 text-sm text-slate-100 shadow-lg"
            >
              Please report the bug <a href={reportHref} className="underline">here</a> with screenshots.
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
