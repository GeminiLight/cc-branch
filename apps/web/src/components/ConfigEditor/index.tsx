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
  Info,
} from "lucide-react";
import { APIRequestError } from "../../api/client";
import type { ConfigIssue } from "../../types";
import { useI18n } from "../../i18n";
import { useToast } from "../ui/Toast";
import LineEditor from "../ui/LineEditor";
import { useConfig, useSaveConfig, useKeyboardShortcuts, useAgents } from "../../hooks";
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
type IssueTone = "danger" | "warning" | "info";

function hasYamlComments(value: string): boolean {
  return value.split("\n").some((line) => line.trimStart().startsWith("#"));
}

function issueTone(issues: ConfigIssue[]): IssueTone {
  if (issues.some((issue) => issue.severity === "error")) return "danger";
  if (issues.some((issue) => issue.severity === "warning")) return "warning";
  return "info";
}

export default function ConfigEditor({ projectPath }: ConfigEditorProps) {
  const { t } = useI18n();
  const toast = useToast();
  const { data, error, isLoading } = useConfig(projectPath);
  const saveMutation = useSaveConfig();

  const [mode, setMode] = useState<EditorMode>("form");
  const { data: agentsData } = useAgents(projectPath, mode === "form");
  const [formData, setFormData] = useState<ConfigFormData>(createDefaultConfig());
  const [yamlContent, setYamlContent] = useState("");
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [copied, setCopied] = useState(false);
  const [saveFlash, setSaveFlash] = useState(false);
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [serverIssues, setServerIssues] = useState<ConfigIssue[] | null>(null);

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
      setServerIssues(null);
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

  const isDirty = useCallback(
    (value: string) => value !== (initialContentRef.current ?? data?.content ?? ""),
    [data?.content]
  );

  /* ── Form change handlers ── */
  const updateForm = useCallback(
    (patch: Partial<ConfigFormData>) => {
      setFormData((prev) => {
        const next = { ...prev, ...patch };
        const yaml = serializeConfigForm(next);
        setYamlContent(yaml);
        setHasUnsavedChanges(isDirty(yaml));
        setFormErrors(validateConfigForm(next, t));
        setServerIssues(null);
        return next;
      });
    },
    [isDirty, t]
  );

  const updateDisplay = useCallback(
    (patch: Partial<ConfigFormData["display"]>) => {
      setFormData((prev) => {
        const next = { ...prev, display: { ...prev.display, ...patch } };
        const yaml = serializeConfigForm(next);
        setYamlContent(yaml);
        setHasUnsavedChanges(isDirty(yaml));
        setServerIssues(null);
        return next;
      });
    },
    [isDirty]
  );

  const updateAgents = useCallback(
    (agents: ConfigFormData["agents"], rename?: { from: string; to: string }) => {
      setFormData((prev) => {
        const slots = rename
          ? prev.slots.map((slot) => ({
              ...slot,
              windows: slot.windows.map((window) => ({
                ...window,
                agent: window.agent === rename.from ? rename.to : window.agent,
              })),
            }))
          : prev.slots;
        const next = { ...prev, agents, slots };
        const yaml = serializeConfigForm(next);
        setYamlContent(yaml);
        setHasUnsavedChanges(isDirty(yaml));
        setServerIssues(null);
        return next;
      });
    },
    [isDirty]
  );

  const updateSlots = useCallback(
    (slots: ConfigFormData["slots"]) => {
      setFormData((prev) => {
        const next = { ...prev, slots };
        const yaml = serializeConfigForm(next);
        setYamlContent(yaml);
        setHasUnsavedChanges(isDirty(yaml));
        setFormErrors(validateConfigForm(next, t));
        setServerIssues(null);
        return next;
      });
    },
    [isDirty, t]
  );

  /* ── YAML change handler ── */
  const handleYamlChange = useCallback(
    (value: string) => {
      setYamlContent(value);
      setHasUnsavedChanges(isDirty(value));
      setServerIssues(null);
      if (yamlValidateTimerRef.current) clearTimeout(yamlValidateTimerRef.current);
      yamlValidateTimerRef.current = setTimeout(() => {
        try {
          YAML.load(value);
          setYamlError(null);
          // Also sync to form data if valid
          const parsed = parseConfigYaml(value);
          setFormData(parsed);
          setFormErrors(validateConfigForm(parsed, t));
        } catch (e: unknown) {
          setYamlError(String(e));
        }
      }, 200);
    },
    [isDirty, t]
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
          setFormErrors(validateConfigForm(parsed, t));
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
      const result = await saveMutation.mutateAsync({
        content: contentToSave,
        projectPath,
        baseMtime: data?.mtime,
        baseContentHash: data?.content_hash,
      });
      initialContentRef.current = contentToSave;
      setYamlContent(contentToSave);
      if (mode === "yaml") {
        setFormData(parseConfigYaml(contentToSave));
      }
      setHasUnsavedChanges(false);
      setYamlError(null);
      setServerIssues(result.issues ?? []);
      setSaveFlash(true);
      if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
      flashTimerRef.current = setTimeout(() => setSaveFlash(false), 1500);
      toast.success(result.diagnostics ? t("configSavedNoRestart") : t("configSaved"));
    } catch (e: unknown) {
      if (e instanceof APIRequestError) {
        if (e.issues?.length) {
          setServerIssues(e.issues);
        }
        if (e.code === "config_conflict") {
          toast.error(t("configConflict"));
        } else {
          toast.error(e.message);
        }
      } else {
        toast.error(e instanceof Error ? e.message : String(e));
      }
    }
  }, [projectPath, mode, formData, yamlContent, formErrors, saveMutation, toast, t, data?.mtime, data?.content_hash]);

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
      <div className="surface-card border border-default rounded-lg page-shell p-4 space-y-4 animate-stagger">
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
  const displayedIssues = serverIssues ?? (!hasUnsavedChanges ? data?.issues ?? [] : []);
  const displayedIssueTone = issueTone(displayedIssues);
  const displayedIssueClass =
    displayedIssueTone === "danger"
      ? "border-[var(--danger)]/15 bg-[var(--danger-bg)] text-[var(--danger)]"
      : displayedIssueTone === "warning"
        ? "border-[var(--warning)]/20 bg-[var(--warning-bg)] text-[var(--warning)]"
        : "border-default bg-[var(--bg-hover)] text-secondary";
  const referencedAgents = formData.slots.flatMap((slot) => [
    slot.agent,
    ...slot.windows.map((window) => window.agent),
  ]).filter((agent): agent is string => Boolean(agent));
  const effectiveAgentNames = Array.from(new Set([
    ...(agentsData?.agents.map((agent) => agent.id) || []),
    ...Object.keys(formData.agents),
    ...referencedAgents,
  ]));

  return (
    <div className="page-shell">
      {/* Header actions */}
      <div className="mb-3 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <FileCode2 className="w-4 h-4 text-tertiary" />
            <h2 className="text-[15px] font-semibold text-primary">
              {t("configuration")}
            </h2>
            {hasUnsavedChanges && (
              <span className="rounded-md bg-[var(--warning-bg)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--warning)]">
                {t("unsaved")}
              </span>
            )}
          </div>
          {data?.path && (
            <p className="mt-1 text-[11px] text-tertiary font-mono truncate">
              {data.path}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center bg-[var(--bg-hover)] rounded-md p-0.5">
            <button
              type="button"
              onClick={() => switchMode("form")}
              className={`control-touch px-3 rounded-md text-[12px] font-medium flex items-center gap-1.5 transition-colors ${
                mode === "form"
                  ? "bg-[var(--bg-card)] text-primary shadow-sm"
                  : "text-tertiary hover:text-secondary"
              }`}
            >
              <LayoutList className="w-3.5 h-3.5" />
              Form
            </button>
            <button
              type="button"
              onClick={() => switchMode("yaml")}
              className={`control-touch px-3 rounded-md text-[12px] font-medium flex items-center gap-1.5 transition-colors ${
                mode === "yaml"
                  ? "bg-[var(--bg-card)] text-primary shadow-sm"
                  : "text-tertiary hover:text-secondary"
              }`}
            >
              <Code2 className="w-3.5 h-3.5" />
              YAML
            </button>
          </div>

          <button
            type="button"
            onClick={copy}
            className="control-touch px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center gap-1.5"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-[var(--success)]" />
                <span className="text-[var(--success)]">{t("copied")}</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                {t("copy")}
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleSave}
            disabled={saveMutation.isPending || !hasUnsavedChanges || (!!yamlError && mode === "yaml") || (formErrors.length > 0 && mode === "form")}
            className="control-touch px-3 rounded-md text-[12px] font-semibold bg-[var(--accent)] text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
          >
            {saveMutation.isPending ? (
              <div className="w-3.5 h-3.5 border-2 border-white/50 border-t-white rounded-full animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            {t("save")}
          </button>
        </div>
      </div>

      {/* Validation / save status */}
      <div className="mb-3 rounded-md border border-default bg-[var(--bg-hover)] px-3 py-2 flex items-start gap-2">
        <Info className="w-3.5 h-3.5 text-tertiary shrink-0 mt-0.5" />
        <p className="text-[11px] text-secondary leading-relaxed">
          {t("configSaveRuntimeHint")}
        </p>
      </div>

      {displayedIssues.length > 0 && (
        <div className={`mb-3 rounded-md border px-3 py-2 flex items-start gap-2 ${displayedIssueClass}`}>
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <div className="space-y-0.5 min-w-0">
            {displayedIssues.map((issue, i) => (
              <p key={`${issue.issue_type}:${issue.target}:${i}`} className="text-[11px] leading-relaxed">
                {issue.message}
              </p>
            ))}
          </div>
        </div>
      )}

      {(mode === "form" ? formErrors : yamlError ? [yamlError] : []).length > 0 && (
        <div className="mb-3 rounded-md border border-[var(--danger)]/15 bg-[var(--danger-bg)] px-3 py-2 flex items-start gap-2">
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

      {saveFlash && (
        <div className="mb-3 rounded-md border border-[var(--success)]/15 bg-[var(--success-bg)] px-3 py-2 flex items-center gap-2">
          <Check className="w-3.5 h-3.5 text-[var(--success)]" />
          <span className="text-[11px] text-[var(--success)] font-medium">
            {t("configSavedNoRestart")}
          </span>
        </div>
      )}

      {/* Editor body */}
      {mode === "form" ? (
        <div className="surface-card border border-default rounded-lg p-1.5 space-y-1 shadow-sm">
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
            agents={effectiveAgentNames}
            onChange={updateSlots}
            expanded={expandedSections.slots}
            onToggle={() => toggleSection("slots")}
          />

          {/* YAML preview sidebar (collapsible) */}
          <details className="group rounded-lg bg-transparent">
            <summary className="px-4 py-3 flex items-center gap-2 cursor-pointer select-none rounded-lg hover:surface-hover transition-colors">
              <ChevronDown className="w-3.5 h-3.5 text-tertiary transition-transform group-open:rotate-180" />
              <Code2 className="w-3.5 h-3.5 text-tertiary" />
              <span className="text-[12px] font-medium text-secondary">{t("generatedYaml")}</span>
            </summary>
            <div className="px-4 pb-4">
              <pre className="language-yaml !border-0 !m-0 max-h-80 overflow-auto rounded-lg bg-[var(--editor-bg)]">
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
