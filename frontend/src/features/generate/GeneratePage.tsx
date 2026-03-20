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

function detectLanguageFromCode(source: string): Language {
  const code = source.trim();
  if (!code) return "python";

  if (/\bpackage\s+[\w.]+\s*;|\bpublic\s+class\b|\bSystem\.out\.println\b/.test(code)) {
    return "java";
  }
  if (/\binterface\s+\w+\b|\btype\s+\w+\s*=|:\s*(string|number|boolean)\b|\bimplements\b/.test(code)) {
    return "typescript";
  }
  if (/\bfunction\b|\bconst\b|\blet\b|=>|\bconsole\.log\b/.test(code)) {
    return "javascript";
  }
  return "python";
}

export function GeneratePage() {
  const [userPrompt, setUserPrompt] = useState("");
  const [code, setCode] = useState(DEFAULT_CODE);
  const [detectedLanguage, setDetectedLanguage] = useState<Language>(detectLanguageFromCode(DEFAULT_CODE));
  const [filename, setFilename] = useState("");
  const [autoCommitEnabled, setAutoCommitEnabled] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | undefined>();
  const [fileInputKey, setFileInputKey] = useState(0);

  const generateMutation = useGenerateMutation();

  const generatedCodeLanguage = useMemo(() => detectedLanguage, [detectedLanguage]);
  const inputMode: InputMode = uploadFile ? "upload" : "paste";

  useEffect(() => {
    const clearForm = () => {
      setUserPrompt("");
      setUploadFile(undefined);
      setCode("");
      setDetectedLanguage("python");
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
        language: inputMode === "paste" ? detectedLanguage : undefined,
        filename: filename || undefined,
        upload_file: uploadFile,
        auto_commit_enabled: autoCommitEnabled,
      });
      toast.success(`Generated tests for job ${response.job_id}`);
    } catch (error) {
      toast.error((error as Error).message || "Generation failed");
    }
  };

  const response = generateMutation.data;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(300px,1.1fr)_minmax(400px,1fr)]">
      <Card>
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-white">Generate Tests</h3>
          <p className="text-sm text-slate-400">Paste source code or upload a file to generate robust tests.</p>
        </div>

        <label className="mb-3 block text-sm">
          <span className="mb-1 block text-slate-300">User Prompt</span>
          <textarea
            className="focus-ring h-24 w-full rounded-lg border border-white/10 bg-ink-900 px-3 py-2 text-slate-100"
            value={userPrompt}
            onChange={(event) => setUserPrompt(event.target.value)}
            placeholder="Describe intent, edge cases, framework preference..."
          />
        </label>

        <div className="mb-3 rounded-lg border border-white/10 bg-ink-900 px-3 py-2 text-sm text-slate-300">
          Detected language: <span className="font-semibold text-white">{detectedLanguage}</span>
        </div>

        <label className="mb-3 block text-sm">
          <span className="mb-1 block text-slate-300">Upload File (optional)</span>
          <input
            key={fileInputKey}
            type="file"
            className="focus-ring w-full rounded-lg border border-dashed border-white/20 bg-ink-900 px-3 py-3"
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

        <div className="overflow-hidden rounded-lg border border-white/10">
          <CodeViewer
            code={code}
            language={detectedLanguage}
            readOnly={false}
            onChange={(nextCode) => {
              setCode(nextCode);
              setDetectedLanguage(detectLanguageFromCode(nextCode));
            }}
            height={300}
          />
        </div>

        <div className="mt-3 grid gap-3">
          <label className="flex items-center gap-2 rounded-lg border border-white/10 bg-ink-900 px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={autoCommitEnabled}
              onChange={(event) => setAutoCommitEnabled(event.target.checked)}
              className="h-4 w-4 accent-cyan-400"
            />
            <span>Auto commit enabled</span>
          </label>
        </div>

        <button
          className="focus-ring mt-4 w-full rounded-lg bg-gradient-to-r from-accent-blue to-accent-magenta px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          onClick={submit}
          disabled={generateMutation.isPending}
        >
          {generateMutation.isPending ? "Generating..." : "Generate Tests"}
        </button>
      </Card>

      <Card>
        <h3 className="mb-3 text-lg font-semibold text-white">Output</h3>
        {!response ? (
          <p className="text-sm text-slate-400">Generated tests, quality score, and warnings will appear here.</p>
        ) : (
          <div className="space-y-3">
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
              <CodeViewer code={response.generated_test_code || ""} language={generatedCodeLanguage} height={360} />
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
