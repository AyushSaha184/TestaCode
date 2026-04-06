import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { Card } from "@/components/common/Card";
import { CodeViewer } from "@/components/common/CodeViewer";
import { ErrorState } from "@/components/common/ErrorState";
import { Skeleton } from "@/components/common/Skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useGenerateMutation } from "@/hooks/queries/useGenerateMutation";
import { useJobDetailQuery } from "@/hooks/queries/useJobDetailQuery";
import type { GenerationResponse, InputMode, JobDetail, Language } from "@/types/api";

const CLEAR_FORM_EVENT = "testacode:clear-generate-form";
const DEFAULT_CODE = "";
const LANGUAGE_OPTIONS: Array<{ label: string; value: Language }> = [
  { label: "Python", value: "python" },
  { label: "JavaScript", value: "javascript" },
  { label: "TypeScript", value: "typescript" },
  { label: "Java", value: "java" },
  { label: "Rust", value: "rust" },
  { label: "Go", value: "golang" },
  { label: "C#", value: "csharp" },
];

function detectLanguageFromCode(source: string): Language | null {
  const code = source.trim();
  if (!code) return null;

  const checks: Array<{ language: Language; patterns: RegExp[] }> = [
    {
      language: "rust",
      patterns: [/\bfn\s+\w+\s*\(/, /\blet\s+mut\b/, /\bimpl\s+\w+/, /\bpub\s+struct\s+\w+/, /\bprintln!\s*\(/, /\buse\s+std::/],
    },
    {
      language: "golang",
      patterns: [
        /^\s*package\s+main\b/m,
        /\bfunc\s+\w+\s*\(/,
        /\bfmt\.Println\s*\(/,
        /:=/,
        /^\s*import\s+\(/m,
        /\btype\s+\w+\s+struct\b/,
      ],
    },
    {
      language: "csharp",
      patterns: [
        /^\s*using\s+System\s*;/m,
        /^\s*namespace\s+[\w.]+\s*[{;]/m,
        /\bpublic\s+class\s+\w+/,
        /\bConsole\.WriteLine\s*\(/,
        /\bstring\[\]\s+args\b/,
        /\[(Test|Fact)\]/,
      ],
    },
    {
      language: "python",
      patterns: [
        /^\s*def\s+\w+\s*\(/m,
        /^\s*class\s+\w+\s*[:(]/m,
        /^\s*from\s+[\w.]+\s+import\s+/m,
        /^\s*import\s+[\w.]+/m,
        /\bself\b/,
        /__name__\s*==\s*["']__main__["']/,
        /\bprint\s*\(/,
      ],
    },
    {
      language: "typescript",
      patterns: [
        /\binterface\s+\w+/,
        /\btype\s+\w+\s*=/,
        /\benum\s+\w+/,
        /\bimplements\s+\w+/,
        /\breadonly\s+\w+/,
        /:\s*(string|number|boolean|unknown|never|any|void)\b/,
        /\b(public|private|protected)\s+\w+/,
        /\bas\s+const\b/,
      ],
    },
    {
      language: "java",
      patterns: [
        /^\s*package\s+[\w.]+\s*;/m,
        /^\s*import\s+java\./m,
        /\bpublic\s+(class|interface|enum)\s+\w+/,
        /\bSystem\.out\.println\s*\(/,
        /\bString\[\]\s+args\b/,
        /@\w+\s+public\s+/,
      ],
    },
    {
      language: "javascript",
      patterns: [
        /\bfunction\s+\w+\s*\(/,
        /\b(const|let|var)\s+\w+/,
        /=>/,
        /\bconsole\.log\s*\(/,
        /\brequire\s*\(/,
        /\bmodule\.exports\b/,
        /\bexport\s+default\b/,
      ],
    },
  ];

  const bestMatch = checks
    .map(({ language, patterns }) => ({
      language,
      score: patterns.reduce((total, pattern) => total + (pattern.test(code) ? 1 : 0), 0),
    }))
    .sort((left, right) => right.score - left.score)[0];

  if (!bestMatch || bestMatch.score === 0) {
    return null;
  }

  return bestMatch.language;
}

function extractRawCode(classifiedIntent: unknown): string {
  if (!classifiedIntent || typeof classifiedIntent !== "object") {
    return "";
  }
  const rawCode = (classifiedIntent as Record<string, unknown>).raw_code;
  return typeof rawCode === "string" ? rawCode : "";
}

function mapJobDetailToGenerationResponse(detail: JobDetail): GenerationResponse {
  return {
    job_id: detail.id,
    detected_language: detail.detected_language,
    generated_test_code: detail.generated_test_code || "",
    quality_score: detail.quality_score ?? 0,
    uncovered_areas: detail.uncovered_areas,
    warnings: detail.warnings,
    framework_used: detail.framework_used || "unspecified",
    output_test_path: detail.output_test_path,
    output_metadata_path: detail.output_metadata_path,
    output_test_url: detail.output_test_url,
    output_metadata_url: detail.output_metadata_url,
    commit_sha: detail.commit_sha,
    ci_status: detail.ci_status,
    ci_conclusion: detail.ci_conclusion,
    ci_run_url: detail.ci_run_url,
    ci_run_id: detail.ci_run_id,
  };
}

interface GenerateNavigationState {
  targetJobId?: string;
  prefillPrompt?: string;
  prefillCode?: string;
}

export function GeneratePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigationState = (location.state as GenerateNavigationState | null) || null;
  const outputJobId = searchParams.get("jobId") || "";
  const matchedPrefillState = navigationState?.targetJobId === outputJobId ? navigationState : null;

  const [userPrompt, setUserPrompt] = useState("");
  const [code, setCode] = useState(DEFAULT_CODE);
  const [autoDetectedLanguage, setAutoDetectedLanguage] = useState<Language | null>(detectLanguageFromCode(DEFAULT_CODE));
  const [languageMode, setLanguageMode] = useState<"auto" | Language>("auto");
  const [filename, setFilename] = useState("");
  const [uploadFile, setUploadFile] = useState<File | undefined>();
  const [fileInputKey, setFileInputKey] = useState(0);
  const [hydratedJobId, setHydratedJobId] = useState<string | null>(null);

  const generateMutation = useGenerateMutation();
  const outputJobQuery = useJobDetailQuery(outputJobId);

  const effectiveLanguage = useMemo(
    () => (languageMode === "auto" ? autoDetectedLanguage ?? "python" : languageMode),
    [autoDetectedLanguage, languageMode],
  );
  const inputMode: InputMode = uploadFile ? "upload" : "paste";

  useEffect(() => {
    setHydratedJobId(null);
  }, [outputJobId]);

  useEffect(() => {
    if (!outputJobQuery.data || hydratedJobId === outputJobQuery.data.id) {
      return;
    }

    if (matchedPrefillState?.prefillPrompt !== undefined) {
      setUserPrompt(matchedPrefillState.prefillPrompt);
    } else {
      setUserPrompt(outputJobQuery.data.user_prompt || "");
    }

    const nextCode =
      matchedPrefillState?.prefillCode !== undefined
        ? matchedPrefillState.prefillCode
        : extractRawCode(outputJobQuery.data.classified_intent);

    setCode(nextCode);
    setAutoDetectedLanguage(detectLanguageFromCode(nextCode));
    setHydratedJobId(outputJobQuery.data.id);

    if (matchedPrefillState) {
      navigate(
        {
          pathname: location.pathname,
          search: location.search,
        },
        {
          replace: true,
          state: null,
        },
      );
    }
  }, [
    hydratedJobId,
    location.pathname,
    location.search,
    matchedPrefillState,
    navigate,
    outputJobQuery.data,
  ]);

  useEffect(() => {
    const clearForm = () => {
      setUserPrompt("");
      setUploadFile(undefined);
      setCode("");
      setAutoDetectedLanguage(null);
      setLanguageMode("auto");
      setFilename("");
      setFileInputKey((previous) => previous + 1);
      setHydratedJobId(null);
      generateMutation.reset();
      setSearchParams({}, { replace: true });
    };

    window.addEventListener(CLEAR_FORM_EVENT, clearForm);
    return () => window.removeEventListener(CLEAR_FORM_EVENT, clearForm);
  }, [generateMutation, setSearchParams]);

  const submit = async () => {
    if (!userPrompt.trim()) {
      toast.error("Prompt is required");
      return;
    }

    try {
      const response = await generateMutation.mutateAsync({
        input_mode: inputMode,
        user_prompt: userPrompt,
        code_content: code,
        language: inputMode === "paste" ? effectiveLanguage : undefined,
        filename: filename || undefined,
        upload_file: uploadFile,
      });
      setSearchParams({ jobId: response.job_id }, { replace: true });
      toast.success("Generated tests successfully");
    } catch (error) {
      toast.error((error as Error).message || "Generation failed");
    }
  };

  const response = outputJobId
    ? outputJobQuery.data
      ? mapJobDetailToGenerationResponse(outputJobQuery.data)
      : undefined
    : generateMutation.data;
  const generatedCodeLanguage = response?.detected_language ?? effectiveLanguage;
  const editorLanguageLabel = languageMode === "auto" ? (autoDetectedLanguage ?? "") : effectiveLanguage;

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
      <div className="flex min-h-[calc(100vh-7.8rem)] flex-col gap-3">
        <Card className="space-y-3">
          <div>
            <h3 className="text-lg font-semibold text-white">Generate Tests</h3>
            <p className="text-sm text-slate-400">Paste source code or upload a file to generate robust tests.</p>
          </div>

          <div className="border-t border-white/10 pt-3">
            <p className="section-label mb-2">User Prompt</p>
            <textarea
              className="input-base h-28 resize-none"
              value={userPrompt}
              onChange={(event) => setUserPrompt(event.target.value)}
              placeholder="Describe intent, edge cases, framework preference..."
            />
          </div>

          <div className="rounded-xl border border-white/10 bg-[#0a1120] px-3 py-2 text-sm">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div className="text-slate-300">
                Language: <span className="font-semibold text-white">{editorLanguageLabel || "auto"}</span>
              </div>
              <label className="flex items-center gap-2 whitespace-nowrap text-xs text-slate-400">
                <span>Mode</span>
                <select
                  className="focus-ring rounded-lg border border-white/12 bg-[#070d1a] px-2 py-1.5 text-sm text-slate-100"
                  value={languageMode}
                  onChange={(event) => setLanguageMode(event.target.value as "auto" | Language)}
                >
                  <option value="auto">Auto-detect</option>
                  {LANGUAGE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <label className="block text-sm">
            <p className="section-label mb-2">Upload File</p>
            <input
              key={fileInputKey}
              type="file"
              className="focus-ring w-full rounded-xl border border-dashed border-white/20 bg-[#0a1120] px-3 py-2.5"
              onChange={(event) => {
                const nextFile = event.target.files?.[0];
                setUploadFile(nextFile);
                if (nextFile) {
                  setFilename(nextFile.name);
                }
              }}
            />
          </label>
        </Card>

        <div className="min-h-0 flex-1 overflow-hidden rounded-xl border border-white/10">
          <CodeViewer
            code={code}
            language={effectiveLanguage}
            readOnly={false}
            onChange={(nextCode) => {
              setCode(nextCode);
              setAutoDetectedLanguage(detectLanguageFromCode(nextCode));
            }}
            height="100%"
          />
        </div>

        <button className="btn-primary btn-primary-full" onClick={submit} disabled={generateMutation.isPending}>
          {generateMutation.isPending ? "Generating..." : "Generate Tests"}
        </button>
      </div>

      <Card className="flex min-h-[calc(100vh-7.8rem)] flex-col">
        <div className="border-b border-white/10 pb-3">
          <h3 className="text-lg font-semibold text-white">Output</h3>
        </div>
        {outputJobId && outputJobQuery.isLoading && !response ? (
          <div className="grid gap-3 py-4">
            <Skeleton className="h-10" />
            <Skeleton className="h-8" />
            <Skeleton className="h-64" />
          </div>
        ) : outputJobId && outputJobQuery.isError ? (
          <div className="pt-4">
            <ErrorState
              title="Unable to load selected output"
              description={(outputJobQuery.error as Error).message}
              onRetry={() => outputJobQuery.refetch()}
            />
          </div>
        ) : !response ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-[#0a1120] text-slate-400">
              <Sparkles size={22} aria-hidden="true" />
            </span>
            <p className="max-w-md text-sm text-slate-400">Generated tests and warnings will appear here.</p>
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pt-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
              <StatusBadge value={response.ci_status || "completed"} />
                <span className="tag-neutral">{response.framework_used}</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(response.generated_test_code || "");
                      toast.success("Generated code copied");
                    } catch {
                      toast.error("Failed to copy code");
                    }
                  }}
                >
                  Copy code
                </button>
                <Link
                  to={`/jobs/${response.job_id}`}
                  state={{
                    targetJobId: response.job_id,
                    prefillPrompt: userPrompt,
                    prefillCode: code,
                  }}
                  className="text-sm text-accent-cyan underline-offset-4 hover:underline"
                >
                  View details -&gt;
                </Link>
              </div>
            </div>

            {(response.output_test_url || response.output_metadata_url) && (
              <div className="grid gap-2 text-sm text-slate-300">
                {response.output_test_url && (
                  <a href={response.output_test_url} target="_blank" rel="noreferrer" className="text-accent-cyan underline-offset-4 hover:underline">
                    Open test artifact
                  </a>
                )}
                {response.output_metadata_url && (
                  <a
                    href={response.output_metadata_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-accent-cyan underline-offset-4 hover:underline"
                  >
                    Open metadata artifact
                  </a>
                )}
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              {response.uncovered_areas.map((item) => (
                <span key={item} className="tag-orange">
                  {item}
                </span>
              ))}
            </div>

            <div className="flex flex-wrap gap-2">
              {response.warnings.map((item) => (
                <span key={item} className="tag-red">
                  {item}
                </span>
              ))}
            </div>

            <div className="min-h-[320px] flex-1 overflow-hidden rounded-xl border border-white/10">
              <CodeViewer code={response.generated_test_code || ""} language={generatedCodeLanguage} height="100%" />
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
