/**
 * ConfigEditor — structured form + raw YAML dual-mode config editor.
 *
 * Replaces the old read-only + textarea flow with a rich form UI
 * while keeping full YAML access for power users.
 */

import { useState, useCallback, useEffect, useRef } from "react";
import YAML from "js-yaml";
import Prism from "prismjs";
import "prismjs/components/prism-yaml";
import {
  FileCode2,
  Save,
  Check,
  Copy,
  LayoutList,
  Code2,
  AlertTriangle,
  ChevronDown,
} from "lucide-react";
import { useI18n } from "../../i18n";
import { useToast } from "../ui/Toast";
import LineEditor from "../ui/LineEditor";
import { useConfig, useSaveConfig, useKeyboardShortcuts } from "../../hooks";
import type { ConfigFormData } from "./types";
import { parseConfigYaml, serializeConfigForm, validateConfigForm } from "./yaml-utils";
import { createDefaultConfig } from "./types";
import ProjectSection from "./ProjectSection";
import DisplaySection from "./DisplaySection";
import AgentsSection from "./AgentsSection";
import SlotsSection from "./SlotsSection";

interface ConfigEditorProps {
  projectPath?: string;
}

type EditorMode = "form" | "yaml";

function hasYamlComments(value: string): boolean {
  return value.split("\n").some((line) => line.trimStart().startsWith("#"));
}

export default function ConfigEditor({ projectPath }: ConfigEditorProps) {
  const { t } = useI18n();
  const toast = useToast();
  const { data, error, isLoading } = useConfig(projectPath);
  const saveMutation = useSaveConfig();

  const [mode, setMode] = useState<EditorMode>("form");
  const [formData, setFormData] = useState<ConfigFormData>(createDefaultConfig());
  const [yamlContent, setYamlContent] = useState("");
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [copied, setCopied] = useState(false);
  const [saveFlash, setSaveFlash] = useState(false);
  const [formErrors, setFormErrors] = useState<string[]>([]);

  // Section expand/collapse state
  const [expandedSections, setExpandedSections] = useState({
    project: true,
    display: false,
    agents: false,
    slots: true,
  });

  const codeRef = useRef<HTMLElement>(null);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const yamlValidateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const initialContentRef = useRef<string | undefined>(undefined);

  // Sync from API data on initial load only; don't overwrite user edits
  useEffect(() => {
    if (data?.content && data.content !== initialContentRef.current) {
      initialContentRef.current = data.content;
      setYamlContent(data.content);
      const parsed = parseConfigYaml(data.content);
      setFormData(parsed);
      setHasUnsavedChanges(false);
      setYamlError(null);
      setFormErrors([]);
    }
  }, [data?.content]);

  // Prism highlight in YAML preview mode
  useEffect(() => {
    if (mode === "yaml" && !hasUnsavedChanges && codeRef.current && data?.content) {
      Prism.highlightElement(codeRef.current);
    }
  }, [mode, hasUnsavedChanges, data?.content]);

  // Warn before unload
  useEffect(() => {
    if (!hasUnsavedChanges) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [hasUnsavedChanges]);

  // Cleanup timers
  useEffect(() => {
    return () => {
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
      if (yamlValidateTimerRef.current) clearTimeout(yamlValidateTimerRef.current);
    };
  }, []);

  // Keyboard shortcuts
  useKeyboardShortcuts({
    onSave: () => {
      if (hasUnsavedChanges && !saveMutation.isPending) {
        handleSave();
      }
    },
  });

  const toggleSection = useCallback((key: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  /* ── Form change handlers ── */
  const updateForm = useCallback(
    (patch: Partial<ConfigFormData>) => {
      setFormData((prev) => {
        const next = { ...prev, ...patch };
        const yaml = serializeConfigForm(next);
        setYamlContent(yaml);
        setHasUnsavedChanges(yaml !== (data?.content || ""));
        setFormErrors(validateConfigForm(next));
        return next;
      });
    },
    [data?.content]
  );

  const updateDisplay = useCallback(
    (patch: Partial<ConfigFormData["display"]>) => {
      setFormData((prev) => {
        const next = { ...prev, display: { ...prev.display, ...patch } };
        const yaml = serializeConfigForm(next);
        setYamlContent(yaml);
        setHasUnsavedChanges(yaml !== (data?.content || ""));
        return next;
      });
    },
    [data?.content]
  );

  const updateAgents = useCallback(
    (agents: ConfigFormData["agents"]) => {
      setFormData((prev) => {
        const next = { ...prev, agents };
        const yaml = serializeConfigForm(next);
        setYamlContent(yaml);
        setHasUnsavedChanges(yaml !== (data?.content || ""));
        return next;
      });
    },
    [data?.content]
  );

  const updateSlots = useCallback(
    (slots: ConfigFormData["slots"]) => {
      setFormData((prev) => {
        const next = { ...prev, slots };
        const yaml = serializeConfigForm(next);
        setYamlContent(yaml);
        setHasUnsavedChanges(yaml !== (data?.content || ""));
        setFormErrors(validateConfigForm(next));
        return next;
      });
    },
    [data?.content]
  );

  /* ── YAML change handler ── */
  const handleYamlChange = useCallback(
    (value: string) => {
      setYamlContent(value);
      setHasUnsavedChanges(value !== (data?.content || ""));
      if (yamlValidateTimerRef.current) clearTimeout(yamlValidateTimerRef.current);
      yamlValidateTimerRef.current = setTimeout(() => {
        try {
          YAML.load(value);
          setYamlError(null);
          // Also sync to form data if valid
          const parsed = parseConfigYaml(value);
          setFormData(parsed);
          setFormErrors(validateConfigForm(parsed));
        } catch (e: unknown) {
          setYamlError(String(e));
        }
      }, 200);
    },
    [data?.content]
  );

  /* ── Mode switch ── */
  const switchMode = useCallback(
    (newMode: EditorMode) => {
      if (newMode === "yaml") {
        // Form → YAML: re-serialize current form state
        const yaml = serializeConfigForm(formData);
        setYamlContent(yaml);
        setYamlError(null);
      } else {
        if (mode === "yaml" && hasYamlComments(yamlContent)) {
          const ok = window.confirm(t("commentsWillBeLost"));
          if (!ok) return;
        }
        // YAML → Form: re-parse current yaml
        try {
          const parsed = parseConfigYaml(yamlContent);
          setFormData(parsed);
          setFormErrors(validateConfigForm(parsed));
          setYamlError(null);
        } catch {
          // Keep current form data if YAML is invalid
        }
      }
      setMode(newMode);
    },
    [formData, mode, t, yamlContent]
  );

  /* ── Save ── */
  const handleSave = useCallback(async () => {
    if (!projectPath) return;
    const contentToSave = mode === "form" ? serializeConfigForm(formData) : yamlContent;
    if (formErrors.length > 0 && mode === "form") {
      toast.error(formErrors[0]);
      return;
    }
    try {
      await saveMutation.mutateAsync({ content: contentToSave, projectPath });
      setHasUnsavedChanges(false);
      setYamlError(null);
      setSaveFlash(true);
      if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
      flashTimerRef.current = setTimeout(() => setSaveFlash(false), 1500);
      toast.success(t("configSaved"));
    } catch (e: unknown) {
      toast.error(String(e));
    }
  }, [projectPath, mode, formData, yamlContent, formErrors, saveMutation, toast, t]);

  /* ── Copy ── */
  const copy = useCallback(async () => {
    const text = mode === "form" ? serializeConfigForm(formData) : yamlContent;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
    copyTimerRef.current = setTimeout(() => setCopied(false), 2000);
  }, [mode, formData, yamlContent]);

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

  const currentYaml = mode === "form" ? serializeConfigForm(formData) : yamlContent;

  return (
    <div className="max-w-3xl">
      {/* Toolbar */}
      <div className="surface-card border border-default rounded-lg mb-3">
        <div className="px-4 py-2.5 border-b border-default flex items-center justify-between flex-wrap gap-2">
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
            {hasUnsavedChanges && (
              <span className="text-[10px] text-[var(--warning)] font-medium">
                • unsaved
              </span>
            )}
          </div>

          <div className="flex items-center gap-1">
            {/* Mode toggle */}
            <div className="flex items-center bg-[var(--bg-hover)] rounded-md p-0.5 mr-2">
              <button
                type="button"
                onClick={() => switchMode("form")}
                className={`h-6 px-2 rounded text-[11px] font-medium flex items-center gap-1 transition-colors ${
                  mode === "form"
                    ? "bg-[var(--bg-card)] text-primary shadow-sm"
                    : "text-tertiary hover:text-secondary"
                }`}
              >
                <LayoutList className="w-3 h-3" />
                Form
              </button>
              <button
                type="button"
                onClick={() => switchMode("yaml")}
                className={`h-6 px-2 rounded text-[11px] font-medium flex items-center gap-1 transition-colors ${
                  mode === "yaml"
                    ? "bg-[var(--bg-card)] text-primary shadow-sm"
                    : "text-tertiary hover:text-secondary"
                }`}
              >
                <Code2 className="w-3 h-3" />
                YAML
              </button>
            </div>

            <button
              type="button"
              onClick={copy}
              className="h-7 px-2 rounded text-[11px] font-medium text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center gap-1"
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

            <button
              type="button"
              onClick={handleSave}
              disabled={saveMutation.isPending || !hasUnsavedChanges || (!!yamlError && mode === "yaml") || (formErrors.length > 0 && mode === "form")}
              className="h-7 px-2 rounded text-[11px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saveMutation.isPending ? (
                <div className="w-3 h-3 border-2 border-white/50 border-t-white rounded-full animate-spin" />
              ) : (
                <Save className="w-3 h-3" />
              )}
              {t("save")}
            </button>
          </div>
        </div>

        {/* Validation errors bar */}
        {(mode === "form" ? formErrors : yamlError ? [yamlError] : []).length > 0 && (
          <div className="px-4 py-2 border-b border-default bg-[var(--danger-bg)] flex items-start gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-[var(--danger)] shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              {(mode === "form" ? formErrors : [yamlError!]).map((err, i) => (
                <p key={i} className="text-[11px] text-[var(--danger)]">
                  {err}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Save success flash */}
        {saveFlash && (
          <div className="px-4 py-2 border-b border-default bg-[var(--success-bg)] flex items-center gap-1.5">
            <Check className="w-3.5 h-3.5 text-[var(--success)]" />
            <span className="text-[11px] text-[var(--success)] font-medium">
              {t("configSaved")}
            </span>
          </div>
        )}
      </div>

      {/* Editor body */}
      {mode === "form" ? (
        <div className="space-y-3">
          <ProjectSection
            data={formData}
            onChange={updateForm}
            expanded={expandedSections.project}
            onToggle={() => toggleSection("project")}
          />
          <DisplaySection
            data={formData.display}
            onChange={updateDisplay}
            expanded={expandedSections.display}
            onToggle={() => toggleSection("display")}
          />
          <AgentsSection
            agents={formData.agents}
            onChange={updateAgents}
            expanded={expandedSections.agents}
            onToggle={() => toggleSection("agents")}
          />
          <SlotsSection
            slots={formData.slots}
            agents={Object.keys(formData.agents)}
            onChange={updateSlots}
            expanded={expandedSections.slots}
            onToggle={() => toggleSection("slots")}
          />

          {/* YAML preview sidebar (collapsible) */}
          <details className="group border border-default rounded-lg surface-card overflow-hidden">
            <summary className="px-3 py-2.5 flex items-center gap-2 cursor-pointer select-none hover:surface-hover transition-colors">
              <ChevronDown className="w-3.5 h-3.5 text-tertiary transition-transform group-open:rotate-180" />
              <Code2 className="w-3.5 h-3.5 text-tertiary" />
              <span className="text-[12px] font-medium text-secondary">Generated YAML</span>
            </summary>
            <div className="border-t border-default">
              <pre className="language-yaml !rounded-none !border-0 !m-0 max-h-80 overflow-auto">
                <code ref={codeRef} className="language-yaml">
                  {currentYaml}
                </code>
              </pre>
            </div>
          </details>
        </div>
      ) : (
        <div className={`surface-card border border-default rounded-lg overflow-hidden transition-all ${saveFlash ? "save-flash-editor" : ""}`}>
          <LineEditor value={yamlContent} onChange={handleYamlChange} error={yamlError} />
        </div>
      )}
    </div>
  );
}
