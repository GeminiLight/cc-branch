import { useRef, useState, useEffect, useCallback } from "react";
import { AlertTriangle } from "lucide-react";
import { useI18n } from "../../i18n";

interface LineEditorProps {
  value: string;
  onChange: (value: string) => void;
  error?: string | null;
}

export default function LineEditor({ value, onChange, error }: LineEditorProps) {
  const { t } = useI18n();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);
  const [lineCount, setLineCount] = useState(1);

  const lines = value.split("\n").length;

  useEffect(() => {
    setLineCount(Math.max(1, lines));
  }, [lines]);

  const handleScroll = useCallback(() => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Tab") {
        e.preventDefault();
        const target = e.currentTarget;
        const start = target.selectionStart;
        const end = target.selectionEnd;
        const newValue = value.substring(0, start) + "  " + value.substring(end);
        onChange(newValue);
        requestAnimationFrame(() => {
          target.selectionStart = target.selectionEnd = start + 2;
        });
      }
    },
    [value, onChange]
  );

  return (
    <div className="relative flex h-[60vh]">
      {/* Line numbers */}
      <div
        ref={lineNumbersRef}
        className="shrink-0 w-10 py-4 pr-2 text-right text-[12.5px] font-mono text-muted select-none overflow-hidden bg-[var(--editor-bg)] border-r border-[var(--editor-border)]"
        aria-hidden="true"
      >
        {Array.from({ length: lineCount }, (_, i) => (
          <div key={i} className="leading-[1.65]">
            {i + 1}
          </div>
        ))}
      </div>

      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onScroll={handleScroll}
        className="flex-1 h-full py-4 px-3 text-[12.5px] font-mono text-[var(--editor-fg)] bg-[var(--editor-bg)] resize-none focus:outline-none leading-[1.65]"
        spellCheck={false}
        aria-label={t("configurationEditor")}
      />

      {/* Error overlay */}
      {error && (
        <div className="absolute bottom-2 left-2 right-2 p-2 rounded bg-[var(--danger-bg)] border border-[var(--danger)]/10 flex items-start gap-1.5 z-10">
          <AlertTriangle className="w-3 h-3 text-[var(--danger)] shrink-0 mt-0.5" />
          <p className="text-[11px] text-[var(--danger)]">{error}</p>
        </div>
      )}
    </div>
  );
}
