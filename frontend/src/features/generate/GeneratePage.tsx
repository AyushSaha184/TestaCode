import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import { Card } from "@/components/common/Card";
import { CodeViewer } from "@/components/common/CodeViewer";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useGenerateMutation } from "@/hooks/queries/useGenerateMutation";
import type { InputMode, Language } from "@/types/api";

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

function detectLanguageFromCode(source: string): Language {
  const code = source.trim();
  if (!code) return "python";

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
    return "python";
  }

  return bestMatch.language;
}

export function GeneratePage() {
  const [userPrompt, setUserPrompt] = useState("");
  const [code, setCode] = useState(DEFAULT_CODE);
  const [autoDetectedLanguage, setAutoDetectedLanguage] = useState<Language>(detectLanguageFromCode(DEFAULT_CODE));
  const [languageMode, setLanguageMode] = useState<"auto" | Language>("auto");
  const [filename, setFilename] = useState("");
  const [uploadFile, setUploadFile] = useState<File | undefined>();
  const [fileInputKey, setFileInputKey] = useState(0);

  const generateMutation = useGenerateMutation();

  const effectiveLanguage = useMemo(
    () => (languageMode === "auto" ? autoDetectedLanguage : languageMode),
    [autoDetectedLanguage, languageMode],
  );
  const inputMode: InputMode = uploadFile ? "upload" : "paste";

  useEffect(() => {
    const clearForm = () => {
      setUserPrompt("");
      setUploadFile(undefined);
      setCode("");
      setAutoDetectedLanguage("python");
      setLanguageMode("auto");
      setFilename("");
      setFileInputKey((previous) => previous + 1);
      generateMutation.reset();
    };

    window.addEventListener(CLEAR_FORM_EVENT, clearForm);
    return () => window.removeEventListener(CLEAR_FORM_EVENT, clearForm);
  }, [generateMutation]);

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
      toast.success(`Generated tests for job ${response.job_id}`);
    } catch (error) {
      toast.error((error as Error).message || "Generation failed");
    }
  };

  const response = generateMutation.data;
  const generatedCodeLanguage = response?.detected_language ?? effectiveLanguage;

  return (
    <div className="grid gap-3 xl:grid-cols-[minmax(320px,0.98fr)_minmax(360px,1.02fr)]">
      <Card className="xl:flex xl:h-[calc(100vh-7.5rem)] xl:flex-col">
        <div className="mb-3">
          <h3 className="text-lg font-semibold text-white">Generate Tests</h3>
          <p className="text-sm text-slate-400">Paste source code or upload a file to generate robust tests.</p>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-3">
          <label className="block text-sm">
            <span className="mb-1 block text-slate-300">User Prompt</span>
            <textarea
              className="focus-ring h-20 w-full resize-none rounded-lg border border-white/10 bg-ink-900 px-3 py-2 text-slate-100"
              value={userPrompt}
              onChange={(event) => setUserPrompt(event.target.value)}
              placeholder="Describe intent, edge cases, framework preference..."
            />
          </label>

          <div className="rounded-lg border border-white/10 bg-ink-900 px-3 py-2 text-sm text-slate-300">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-2">
                <span>
                  Editor language: <span className="font-semibold text-white">{effectiveLanguage}</span>
                </span>
                <span className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[11px] uppercase tracking-[0.14em] text-slate-400">
                  {languageMode === "auto" ? "Auto Detected" : "Manual"}
                </span>
              </div>
              <label className="flex items-center gap-2 whitespace-nowrap text-xs text-slate-400">
                <span>Mode</span>
                <select
                  className="focus-ring rounded-md border border-white/10 bg-ink-950 px-2 py-1 text-sm text-slate-100"
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
            <span className="mb-1 block text-slate-300">Upload File (optional)</span>
            <input
              key={fileInputKey}
              type="file"
              className="focus-ring w-full rounded-lg border border-dashed border-white/20 bg-ink-900 px-3 py-2.5"
              onChange={(event) => {
                const nextFile = event.target.files?.[0];
                setUploadFile(nextFile);
                if (nextFile) {
                  setFilename(nextFile.name);
                }
              }}
            />
            <p className="mt-1 text-xs text-slate-400">If a file is selected, upload mode is used automatically.</p>
          </label>

          <div className="min-h-0 flex-1 overflow-hidden rounded-lg border border-white/10">
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

          <button
            className="focus-ring w-full rounded-lg bg-gradient-to-r from-accent-blue to-accent-magenta px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            onClick={submit}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending ? "Generating..." : "Generate Tests"}
          </button>
        </div>
      </Card>

      <Card className="xl:flex xl:h-[calc(100vh-7.5rem)] xl:flex-col">
        <h3 className="mb-3 text-lg font-semibold text-white">Output</h3>
        {!response ? (
          <p className="text-sm text-slate-400">Generated tests, quality score, and warnings will appear here.</p>
        ) : (
          <div className="min-h-0 space-y-3 xl:flex-1 xl:overflow-y-auto">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge value={response.ci_status || "completed"} />
              <span className="rounded-full border border-accent-cyan/40 bg-accent-cyan/10 px-2 py-1 text-xs font-semibold text-accent-cyan">
                Quality {response.quality_score}/10
              </span>
              <span className="rounded-full border border-white/20 px-2 py-1 text-xs text-slate-200">{response.framework_used}</span>
            </div>

            <div className="text-sm text-slate-300">
              Job: <span className="font-mono text-slate-100">{response.job_id}</span>{" "}
              <Link to={`/jobs/${response.job_id}`} className="text-accent-cyan underline-offset-4 hover:underline">
                View Details
              </Link>
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
                <span key={item} className="rounded-full border border-accent-orange/40 bg-accent-orange/10 px-2 py-1 text-xs text-accent-orange">
                  {item}
                </span>
              ))}
            </div>

            <div className="flex flex-wrap gap-2">
              {response.warnings.map((item) => (
                <span key={item} className="rounded-full border border-accent-red/40 bg-accent-red/10 px-2 py-1 text-xs text-accent-red">
                  {item}
                </span>
              ))}
            </div>

            <div className="overflow-hidden rounded-lg border border-white/10">
              <CodeViewer code={response.generated_test_code || ""} language={generatedCodeLanguage} height={320} />
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
