import Editor from "@monaco-editor/react";
import { useMemo } from "react";
import type { Language } from "@/types/api";

interface CodeViewerProps {
  code: string;
  language: Language;
  readOnly?: boolean;
  onChange?: (next: string) => void;
  height?: number | string;
}

function toMonacoLang(language: Language): string {
  if (language === "python") return "python";
  if (language === "javascript") return "javascript";
  if (language === "typescript") return "typescript";
  if (language === "rust") return "rust";
  if (language === "golang") return "go";
  if (language === "csharp") return "csharp";
  return "java";
}

export function CodeViewer({ code, language, readOnly = true, onChange, height = 360 }: CodeViewerProps) {
  const options = useMemo(
    () => ({
      readOnly,
      fontSize: 13,
      minimap: { enabled: false },
      roundedSelection: true,
      scrollBeyondLastLine: false,
      automaticLayout: true,
      wordWrap: "on" as const,
      wrappingIndent: "same" as const,
      padding: { top: 14, bottom: 14 },
    }),
    [readOnly],
  );

  return (
    <Editor
      language={toMonacoLang(language)}
      value={code}
      height={height}
      options={options}
      theme="vs-dark"
      onChange={(value: string | undefined) => {
        if (!readOnly && onChange) onChange(value || "");
      }}
    />
  );
}
