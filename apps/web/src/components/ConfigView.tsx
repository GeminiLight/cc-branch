import { useEffect, useRef, useState, useCallback } from "react";
import Prism from "prismjs";
import "prismjs/components/prism-yaml";
import YAML from "js-yaml";
import { Check, Copy, FileCode2, Pencil, Save, X } from "lucide-react";
import { useI18n } from "../i18n";
import { useToast } from "./ui/Toast";
import LineEditor from "./ui/LineEditor";
import { useConfig, useSaveConfig, useKeyboardShortcuts } from "../hooks";

interface ConfigViewProps {
  projectPath?: string;
}

export default function ConfigView({ projectPath }: ConfigViewProps) {
  const { t } = useI18n();
  const toast = useToast();
  const { data, error, isLoading } = useConfig(projectPath);
  const saveMutation = useSaveConfig();

  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [saveFlash, setSaveFlash] = useState(false);
  const codeRef = useRef<HTMLElement>(null);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const yamlValidateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cmd+S to save when editing
  useKeyboardShortcuts({
    onSave: () => {
      if (editing && hasUnsavedChanges && !yamlError && !saveMutation.isPending) {
        handleSave();
      }
    },
  });

  // Sync editContent when data loads (derived state during render)
  if (data?.content && !editing && editContent !== data.content) {
    setEditContent(data.content);
    setHasUnsavedChanges(false);
  }

  // Prism highlighting
  useEffect(() => {
    if (data?.content && codeRef.current && !editing) {
      Prism.highlightElement(codeRef.current);
    }
  }, [data?.content, editing]);

  // Warn before unload when unsaved
  useEffect(() => {
    if (!hasUnsavedChanges) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [hasUnsavedChanges]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
      if (yamlValidateTimerRef.current) clearTimeout(yamlValidateTimerRef.current);
    };
  }, []);

  const copy = useCallback(async () => {
    if (!data?.content) return;
    try {
      await navigator.clipboard.writeText(data.content);
      setCopied(true);
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = data.content;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => setCopied(false), 2000);
    }
  }, [data]);

  const handleSave = useCallback(async () => {
    if (!projectPath) return;
    try {
      await saveMutation.mutateAsync({ content: editContent, projectPath });
      setEditing(false);
      setHasUnsavedChanges(false);
      setYamlError(null);
      setSaveFlash(true);
      if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
      flashTimerRef.current = setTimeout(() => setSaveFlash(false), 1500);
      toast.success(t("configSaved"));
    } catch (e: unknown) {
      toast.error(String(e));
    }
  }, [editContent, projectPath, saveMutation, toast, t]);

  const handleCancel = useCallback(() => {
    setEditing(false);
    setEditContent(data?.content || "");
    setHasUnsavedChanges(false);
    setYamlError(null);
  }, [data?.content]);

  const handleEditChange = useCallback((value: string) => {
    setEditContent(value);
    setHasUnsavedChanges(value !== (data?.content || ""));
    if (yamlValidateTimerRef.current) clearTimeout(yamlValidateTimerRef.current);
    yamlValidateTimerRef.current = setTimeout(() => {
      try {
        YAML.load(value);
        setYamlError(null);
      } catch (e: unknown) {
        setYamlError(String(e));
      }
    }, 200);
  }, [data?.content]);

  if (isLoading) {
    return (
      <div className="surface-card border border-default rounded-lg max-w-3xl p-4 space-y-4 animate-stagger">
        <div className="flex items-center gap-2">
          <div className="w-24 h-3 bg-[var(--border-subtle)] rounded animate-skeleton" />
          <div className="w-16 h-3 bg-[var(--border-subtle)] rounded animate-skeleton" />
        </div>
        <div className="space-y-2">
          <div className="w-full h-3 bg-[var(--border-subtle)] rounded animate-skeleton" />
          <div className="w-[90%] h-3 bg-[var(--border-subtle)] rounded animate-skeleton" />
          <div className="w-[75%] h-3 bg-[var(--border-subtle)] rounded animate-skeleton" />
          <div className="w-[85%] h-3 bg-[var(--border-subtle)] rounded animate-skeleton" />
          <div className="w-full h-3 bg-[var(--border-subtle)] rounded animate-skeleton" />
          <div className="w-[60%] h-3 bg-[var(--border-subtle)] rounded animate-skeleton" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-sm mx-auto text-center py-20">
        <p className="text-[13px] text-secondary">{String(error)}</p>
      </div>
    );
  }

  return (
    <div className="surface-card border border-default rounded-lg max-w-3xl">
      {/* Toolbar */}
      <div className="px-4 py-2.5 border-b border-default flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileCode2 className="w-3.5 h-3.5 text-tertiary" />
          <span className="text-[11px] font-semibold text-tertiary uppercase tracking-wide">
            {t("configuration")}
          </span>
          {data?.path && (
            <span className="text-[10px] text-muted font-mono">
              {data.path.split("/").pop()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {!editing ? (
            <>
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="h-7 px-2 rounded text-[11px] font-medium text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center gap-1"
                aria-label={t("edit")}
              >
                <Pencil className="w-3 h-3" /> {t("edit")}
              </button>
              <button
                type="button"
                onClick={copy}
                className="h-7 px-2 rounded text-[11px] font-medium text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center gap-1"
                aria-label={t("copy")}
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-[var(--success)]" />
                    <span className="text-[var(--success)]">{t("copied")}</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    {t("copy")}
                  </>
                )}
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={handleCancel}
                className="h-7 px-2 rounded text-[11px] font-medium text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center gap-1"
              >
                <X className="w-3 h-3" /> {t("cancel")}
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saveMutation.isPending || !hasUnsavedChanges || !!yamlError}
                className="h-7 px-2 rounded text-[11px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saveMutation.isPending ? (
                  <div className="w-3 h-3 border-2 border-white/50 border-t-white rounded-full animate-spin" />
                ) : (
                  <Save className="w-3 h-3" />
                )}
                {t("save")}
              </button>
            </>
          )}
        </div>
      </div>

      {editing ? (
        <div className={`relative transition-all ${saveFlash ? "save-flash-editor" : ""}`}>
          <LineEditor
            value={editContent}
            onChange={handleEditChange}
            error={yamlError}
          />
        </div>
      ) : (
        <pre className="language-yaml !rounded-none !border-0 !border-t !border-default !m-0">
          <code ref={codeRef} className="language-yaml">
            {data?.content || t("loading")}
          </code>
        </pre>
      )}
    </div>
  );
}
