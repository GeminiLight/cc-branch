import { useMemo, useState } from "react";
import { ChevronsUpDown, CopyPlus, Layers3, PenLine, Plus, RotateCcw, Save, TerminalSquare, Trash2, X } from "lucide-react";
import { useI18n } from "../i18n";
import Dropdown from "./ui/Dropdown";
import {
  cloneTemplate,
  customProfileTemplates,
  effectiveTemplateSpecs,
  isBuiltInTemplateId,
  loadUserTemplates,
  profileOrder,
  saveUserTemplates,
  templateSpecs,
  templateStats,
  type PreviewPane,
  type TemplateSpec,
} from "./config-wizard-model";

type DraftMode = "new" | "edit";
const TEMPLATE_AGENT_OPTIONS = ["codex", "claude", "gemini", "opencode", "copilot", "cursor", "kimi"];

interface TemplateDraft {
  mode: DraftMode;
  baseId: string;
  originalId: string | null;
  spec: TemplateSpec;
}

function profileLabelKey(id: string): string {
  return `profile${id.charAt(0).toUpperCase()}${id.slice(1)}Name`;
}

function templateDisplayName(t: (key: string, vars?: Record<string, string | number>) => string, template: TemplateSpec): string {
  return template.name || (isBuiltInTemplateId(template.id) ? t(profileLabelKey(template.id)) : template.id);
}

function uniqueTemplateId(name: string, templates: TemplateSpec[]): string {
  const base = name.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "template";
  const ids = new Set(templates.map((template) => template.id));
  let id = `custom-${base}`;
  let index = 2;
  while (ids.has(id)) {
    id = `custom-${base}-${index}`;
    index += 1;
  }
  return id;
}

function patchPane(pane: PreviewPane, patch: Partial<PreviewPane>): PreviewPane {
  return { ...pane, ...patch };
}

function agentForTemplatePane(pane: PreviewPane): string {
  return pane.agent || pane.preferredAgents.find((agent) => TEMPLATE_AGENT_OPTIONS.includes(agent)) || pane.preferredAgents[0] || "codex";
}

export default function TemplateCenterSettings() {
  const { t } = useI18n();
  const [templates, setTemplates] = useState<TemplateSpec[]>(() => loadUserTemplates());
  const [draft, setDraft] = useState<TemplateDraft | null>(null);

  const effectiveSpecs = useMemo(() => effectiveTemplateSpecs(templates), [templates]);
  const customTemplates = useMemo(() => customProfileTemplates(templates), [templates]);
  const baseOptions = useMemo(
    () => profileOrder.map((id) => ({ id, label: t(profileLabelKey(id)) })),
    [t]
  );

  function persist(next: TemplateSpec[]) {
    setTemplates(next);
    saveUserTemplates(next);
  }

  function startNewTemplate() {
    const baseId = profileOrder[0];
    setDraft({
      mode: "new",
      baseId,
      originalId: null,
      spec: { ...cloneTemplate(templateSpecs[baseId]), id: "", name: "" },
    });
  }

  function startEditTemplate(template: TemplateSpec) {
    setDraft({
      mode: "edit",
      baseId: isBuiltInTemplateId(template.id) ? template.id : profileOrder[0],
      originalId: template.id,
      spec: cloneTemplate(template),
    });
  }

  function changeDraftBase(baseId: string) {
    setDraft((current) => {
      if (!current) return current;
      const name = current.spec.name || "";
      return {
        ...current,
        baseId,
        spec: { ...cloneTemplate(templateSpecs[baseId] || templateSpecs.development), id: current.spec.id, name },
      };
    });
  }

  function patchDraftSpec(patch: Partial<TemplateSpec>) {
    setDraft((current) => current ? { ...current, spec: { ...current.spec, ...patch } } : current);
  }

  function renameDraftTab(tabIndex: number, name: string) {
    setDraft((current) => {
      if (!current) return current;
      const spec = cloneTemplate(current.spec);
      spec.tabs[tabIndex] = { ...spec.tabs[tabIndex], name };
      return { ...current, spec };
    });
  }

  function renameDraftPane(tabIndex: number, paneIndex: number, name: string) {
    setDraft((current) => {
      if (!current) return current;
      const spec = cloneTemplate(current.spec);
      const tab = spec.tabs[tabIndex];
      tab.panes[paneIndex] = patchPane(tab.panes[paneIndex], { name });
      return { ...current, spec };
    });
  }

  function changeDraftPaneAgent(tabIndex: number, paneIndex: number, agent: string) {
    setDraft((current) => {
      if (!current) return current;
      const spec = cloneTemplate(current.spec);
      const tab = spec.tabs[tabIndex];
      tab.panes[paneIndex] = patchPane(tab.panes[paneIndex], { agent });
      return { ...current, spec };
    });
  }

  function saveDraft() {
    if (!draft) return;
    const trimmedName = (draft.spec.name || "").trim();
    if (draft.mode === "new" && !trimmedName) return;
    const id = draft.mode === "new"
      ? uniqueTemplateId(trimmedName, templates)
      : draft.originalId || draft.spec.id;
    const nextTemplate = {
      ...cloneTemplate(draft.spec),
      id,
      ...(trimmedName ? { name: trimmedName } : {}),
    };
    const next = templates.filter((template) => template.id !== id);
    persist([...next, nextTemplate]);
    setDraft(null);
  }

  function removeTemplate(id: string) {
    persist(templates.filter((template) => template.id !== id));
    if (draft?.originalId === id) setDraft(null);
  }

  function renderTemplateCard(template: TemplateSpec, builtIn: boolean) {
    const stats = templateStats(template);
    const name = templateDisplayName(t, template);
    const overridden = builtIn && templates.some((item) => item.id === template.id);
    return (
      <div key={template.id} className="rounded-lg border border-default bg-[var(--bg-card)] p-3">
        <div className="flex items-start gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-[var(--accent-border)] bg-[var(--accent-bg)] text-[var(--accent)]">
            <Layers3 className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-semibold text-primary">{name}</p>
            <p className="text-[11px] text-tertiary">
              {t("templateTabsPanes", { tabs: stats.tabs, panes: stats.panes })}
            </p>
          </div>
          <div className="flex items-center gap-1">
            {overridden && (
              <button
                type="button"
                onClick={() => removeTemplate(template.id)}
                className="flex h-7 w-7 items-center justify-center rounded-md text-tertiary transition-colors hover:bg-[var(--bg-hover)] hover:text-primary"
                aria-label={t("resetTemplateNamed", { name })}
                title={t("resetTemplateNamed", { name })}
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
            )}
            <button
              type="button"
              onClick={() => startEditTemplate(template)}
              className="flex h-7 w-7 items-center justify-center rounded-md text-tertiary transition-colors hover:bg-[var(--bg-hover)] hover:text-primary"
              aria-label={t("editTemplateNamed", { name })}
              title={t("editTemplateNamed", { name })}
            >
              <PenLine className="h-3.5 w-3.5" />
            </button>
            {!builtIn && (
              <button
                type="button"
                onClick={() => removeTemplate(template.id)}
                className="flex h-7 w-7 items-center justify-center rounded-md text-tertiary transition-colors hover:bg-[var(--danger-bg)] hover:text-[var(--danger)]"
                aria-label={t("removeTemplateNamed", { name })}
                title={t("removeTemplateNamed", { name })}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        <div className="mt-3 grid gap-2">
          {template.tabs.map((tab, tabIndex) => (
            <div key={`${template.id}-${tabIndex}`} className="rounded-md border border-subtle bg-[var(--bg-elevated)] px-2 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex min-w-0 items-center gap-1.5 text-[11px] font-semibold text-primary">
                  {tab.layoutBackend === "tmux" ? <Layers3 className="h-3.5 w-3.5 text-[var(--accent)]" /> : <TerminalSquare className="h-3.5 w-3.5 text-[var(--accent)]" />}
                  <span className="text-[10px] uppercase text-tertiary">{t("tab")}</span>
                  <span className="truncate font-mono">{tab.name}</span>
                </span>
                <span className="shrink-0 rounded border border-default bg-[var(--bg-card)] px-1.5 py-0.5 text-[10px] font-semibold text-tertiary">
                  {tab.layoutBackend === "tmux" ? t("templateTmuxRuntime") : t("terminalRuntime")}
                </span>
              </div>
              <div className="mt-2 grid gap-1">
                {tab.panes.map((pane, paneIndex) => (
                  <div key={`${template.id}-${tabIndex}-${paneIndex}`} className="grid grid-cols-[48px_minmax(0,1fr)_74px] items-center gap-2 rounded border border-default bg-[var(--bg-card)] px-2 py-1">
                    <span className="text-[10px] font-semibold uppercase text-tertiary">{t("pane")}</span>
                    <span className="truncate font-mono text-[11px] text-primary">{pane.name}</span>
                    <span className="truncate rounded bg-[var(--accent-bg)] px-1.5 py-0.5 text-center font-mono text-[10px] text-[var(--accent)]">
                      {agentForTemplatePane(pane)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-[12px] font-semibold text-primary">{t("templateCenter")}</h4>
        <button
          type="button"
          onClick={startNewTemplate}
          className="h-8 rounded-md bg-[var(--accent)] px-3 text-[12px] font-semibold text-white inline-flex items-center justify-center gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" />
          {t("addTemplate")}
        </button>
      </div>

      {draft && (
        <section
          role="region"
          aria-label={t("templateEditor")}
          className="rounded-lg border border-[var(--accent-border)] bg-[var(--accent-bg)]/35 p-3"
        >
          <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_150px]">
            <input
              value={draft.spec.name || ""}
              onChange={(event) => patchDraftSpec({ name: event.target.value })}
              placeholder={t("templateNamePlaceholder")}
              className="h-8 min-w-0 rounded border border-default bg-[var(--bg-page)] px-2.5 text-[13px] text-primary outline-none focus:border-[var(--accent)]"
              aria-label={t("templateName")}
            />
            {draft.mode === "new" ? (
              <select
                value={draft.baseId}
                onChange={(event) => changeDraftBase(event.target.value)}
                className="h-8 rounded border border-default bg-[var(--bg-page)] px-2 text-[12px] text-primary outline-none focus:border-[var(--accent)]"
                aria-label={t("baseTemplate")}
              >
                {baseOptions.map((option) => (
                  <option key={option.id} value={option.id}>{option.label}</option>
                ))}
              </select>
            ) : null}
          </div>

          <div className="mt-3 space-y-3">
            {draft.spec.tabs.map((tab, tabIndex) => (
              <div key={tabIndex} className="rounded-md border border-default bg-[var(--bg-card)] p-2">
                <div className="grid gap-2 sm:grid-cols-[74px_minmax(0,1fr)_120px] sm:items-center">
                  <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase text-tertiary">
                    {tab.layoutBackend === "tmux" ? <Layers3 className="h-3.5 w-3.5 text-[var(--accent)]" /> : <TerminalSquare className="h-3.5 w-3.5 text-[var(--accent)]" />}
                    {t("tab")}
                  </span>
                  <input
                    value={tab.name}
                    onChange={(event) => renameDraftTab(tabIndex, event.target.value)}
                    className="h-7 w-full rounded border border-default bg-[var(--bg-page)] px-2 font-mono text-[12px] text-primary outline-none focus:border-[var(--accent)]"
                    aria-label={t("tabName")}
                  />
                  <span className="rounded border border-default bg-[var(--bg-page)] px-2 py-1 text-center text-[10px] font-semibold text-tertiary">
                    {tab.layoutBackend === "tmux" ? t("templateTmuxRuntime") : t("terminalRuntime")}
                  </span>
                </div>
                <div className="mt-2 grid gap-1.5">
                  {tab.panes.map((pane, paneIndex) => (
                    <div key={paneIndex} className="grid gap-2 rounded border border-default bg-[var(--bg-elevated)] px-2 py-1.5 sm:grid-cols-[74px_minmax(0,1fr)_142px] sm:items-center">
                      <span className="text-[10px] font-semibold uppercase text-tertiary">{t("pane")}</span>
                      <input
                        value={pane.name}
                        onChange={(event) => renameDraftPane(tabIndex, paneIndex, event.target.value)}
                        className="h-7 min-w-0 rounded border border-default bg-[var(--bg-page)] px-2 font-mono text-[11px] text-primary outline-none focus:border-[var(--accent)]"
                        aria-label={t("windowName")}
                      />
                      <Dropdown
                        value={agentForTemplatePane(pane)}
                        onChange={(agent) => changeDraftPaneAgent(tabIndex, paneIndex, agent)}
                        align="right"
                        ariaLabel={t("agentCli")}
                        className="min-w-0 w-full"
                        triggerClassName="w-full"
                        items={TEMPLATE_AGENT_OPTIONS.map((agent) => ({ label: agent, value: agent }))}
                        trigger={
                          <span className="flex h-7 min-w-0 items-center justify-between gap-1.5 rounded border border-default bg-[var(--bg-page)] px-2 font-mono text-[11px] text-[var(--accent)]">
                            <span className="truncate">{agentForTemplatePane(pane)}</span>
                            <ChevronsUpDown className="h-3 w-3 shrink-0 text-tertiary" />
                          </span>
                        }
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-3 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setDraft(null)}
              className="h-8 rounded px-3 text-[12px] font-medium text-secondary transition-colors hover:bg-[var(--bg-hover)] hover:text-primary inline-flex items-center gap-1.5"
            >
              <X className="h-3.5 w-3.5" />
              {t("cancel")}
            </button>
            <button
              type="button"
              onClick={saveDraft}
              disabled={draft.mode === "new" && !draft.spec.name?.trim()}
              className="h-8 rounded-md bg-[var(--accent)] px-3 text-[12px] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
            >
              <Save className="h-3.5 w-3.5" />
              {t("saveTemplate")}
            </button>
          </div>
        </section>
      )}

      <div className="max-h-[360px] space-y-3 overflow-y-auto pr-1">
        {profileOrder.map((id) => renderTemplateCard(effectiveSpecs[id], true))}
        {customTemplates.map((template) => renderTemplateCard(template, false))}
        {customTemplates.length === 0 && (
          <div className="rounded-md border border-dashed border-default px-3 py-5 text-center">
            <CopyPlus className="mx-auto mb-1.5 h-5 w-5 text-tertiary" />
            <p className="text-[12px] text-secondary">{t("noCustomTemplates")}</p>
          </div>
        )}
      </div>
    </section>
  );
}
