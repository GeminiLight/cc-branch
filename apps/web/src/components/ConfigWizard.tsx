import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import {
  CheckCircle2,
  ChevronsUpDown,
  Code2,
  Feather,
  Layers3,
  Loader2,
  Minimize2,
  Save,
  TerminalSquare,
  Wand2,
  X,
  Zap,
} from "lucide-react";
import { useI18n } from "../i18n";
import { useToast } from "./ui/Toast";
import { useAgents, useProfiles, useSaveConfig } from "../hooks";
import type { Profile } from "../types";
import Dropdown from "./ui/Dropdown";
import {
  cloneTemplate,
  defaultProfileId,
  profileOrder,
  projectNameFromPath,
  selectedAgentForPane,
  templateSpecs,
  templateStats,
  yamlForTemplate,
  type TemplateSpec,
} from "./config-wizard-model";

interface ConfigWizardProps {
  projectPath?: string;
  configPath?: string;
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

type Step = "select" | "done";

const profileIcons: Record<string, React.ReactNode> = {
  development: <Code2 className="w-4 h-4" />,
  design: <Feather className="w-4 h-4" />,
  minimal: <Minimize2 className="w-4 h-4" />,
};

const profileLabelKeys: Record<string, string> = {
  development: "profileDevelopmentName",
  design: "profileDesignName",
  minimal: "profileMinimalName",
};

const profileDescriptionKeys: Record<string, string> = {
  development: "profileDevelopmentDesc",
  design: "profileDesignDesc",
  minimal: "profileMinimalDesc",
};

const fallbackProfiles: Profile[] = [
  { id: "development", description: "" },
  { id: "design", description: "" },
  { id: "minimal", description: "" },
];

function WorkspacePreview({
  spec,
  availableAgents,
  onRenameTab,
  onRenamePane,
  onChangeAgent,
}: {
  spec: TemplateSpec;
  availableAgents: string[];
  onRenameTab: (tabIndex: number, name: string) => void;
  onRenamePane: (tabIndex: number, paneIndex: number, name: string) => void;
  onChangeAgent: (tabIndex: number, paneIndex: number, agent: string) => void;
}) {
  const { t } = useI18n();
  const agentOptions = availableAgents.length > 0 ? availableAgents : ["codex", "claude", "gemini"];
  return (
    <div className="space-y-3">
      {spec.tabs.map((tab, tabIndex) => {
        const panes = tab.layoutBackend === "direct"
          ? [{ name: tab.name, preferredAgents: ["shell"], agent: "shell" }]
          : tab.panes;
        return (
        <section key={tabIndex} className="rounded-lg border border-default bg-[var(--bg-card)] overflow-hidden">
          <div className="grid grid-cols-[86px_minmax(0,1fr)_auto] items-center gap-3 border-b border-default bg-[var(--bg-elevated)] px-3 py-2.5">
            <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase text-tertiary">
              {tab.layoutBackend === "tmux" ? (
                <Layers3 className="w-3.5 h-3.5 text-[var(--accent)] shrink-0" />
              ) : (
                <TerminalSquare className="w-3.5 h-3.5 text-[var(--accent)] shrink-0" />
              )}
              {t("tab")}
            </span>
            <div className="min-w-0">
              <input
                value={tab.name}
                onChange={(e) => onRenameTab(tabIndex, e.target.value)}
                className="w-full min-w-0 cursor-text rounded border border-default bg-[var(--bg-card)] px-2 py-1 font-mono text-[12px] font-semibold text-primary outline-none transition-colors hover:border-[var(--accent-border)] focus:border-[var(--accent-border)]"
                aria-label={t("slotName")}
              />
            </div>
            <span className="rounded border border-default bg-[var(--bg-card)] px-1.5 py-0.5 text-[10px] font-semibold text-tertiary">
              {tab.layoutBackend === "tmux" ? t("templateTmuxRuntime") : t("terminalRuntime")}
            </span>
          </div>

          <div className="p-3 space-y-2">
            {panes.map((pane, paneIndex) => {
                const selectedAgent = selectedAgentForPane(pane, availableAgents);
                const options = agentOptions.includes(selectedAgent)
                  ? agentOptions
                  : [selectedAgent, ...agentOptions];
                return (
                <div
                  key={paneIndex}
                  className="grid grid-cols-[64px_minmax(120px,0.9fr)_minmax(0,1fr)_minmax(104px,auto)] items-center gap-2 rounded-md border border-default bg-[var(--bg-elevated)] px-2 py-1.5"
                >
                  <span className="text-[10px] font-semibold uppercase text-tertiary">{t("pane")}</span>
                  <input
                    value={pane.name}
                    onChange={(e) => {
                      if (tab.layoutBackend === "direct") {
                        onRenameTab(tabIndex, e.target.value);
                        return;
                      }
                      onRenamePane(tabIndex, paneIndex, e.target.value);
                    }}
                    className="min-w-0 cursor-text rounded border border-default bg-[var(--bg-card)] px-2 py-1 font-mono text-[11px] text-primary outline-none transition-colors hover:border-[var(--accent-border)] focus:border-[var(--accent-border)]"
                    aria-label={t("windowName")}
                  />
                  <span className="h-1 rounded-full bg-[var(--accent)]/75" aria-hidden="true" />
                  {tab.layoutBackend === "direct" ? (
                    <span className="min-w-0 w-full rounded-md border border-default bg-[var(--bg-card)] px-2 py-1 text-[10px] font-mono text-tertiary">
                      shell
                    </span>
                  ) : (
                    <Dropdown
                      value={selectedAgent}
                      onChange={(nextAgent) => onChangeAgent(tabIndex, paneIndex, nextAgent)}
                      align="right"
                      aria-label={t("agent")}
                      className="min-w-0 w-full"
                      triggerClassName="w-full"
                      items={options.map((agent) => ({
                        label: agent,
                        value: agent,
                      }))}
                      trigger={
                        <span className="min-w-0 w-full rounded-md border border-default bg-[var(--bg-card)] px-2 py-1 text-[10px] font-mono text-[var(--accent)] transition-colors hover:border-[var(--accent-border)] flex items-center justify-between gap-1.5">
                          <span className="truncate">{selectedAgent}</span>
                          <ChevronsUpDown className="w-3 h-3 text-tertiary shrink-0" />
                        </span>
                      }
                    />
                  )}
                </div>
                );
              })}
          </div>
        </section>
        );
      })}
    </div>
  );
}

export default function ConfigWizard({ projectPath, configPath, isOpen, onClose, onCreated }: ConfigWizardProps) {
  const { t } = useI18n();
  const toast = useToast();
  const { data: profiles } = useProfiles();
  const scope = useMemo(() => ({ projectPath, configPath }), [projectPath, configPath]);
  const { data: agentsData } = useAgents(scope, isOpen);
  const saveMutation = useSaveConfig();

  const [step, setStep] = useState<Step>("select");
  const [selectedProfileId, setSelectedProfileId] = useState(defaultProfileId);
  const [draftSpec, setDraftSpec] = useState<TemplateSpec>(() => cloneTemplate(templateSpecs[defaultProfileId]));
  const modalRef = useRef<HTMLDivElement>(null);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const titleId = useId();

  const visibleProfiles = useMemo(() => {
    const byId = new Map((profiles?.length ? profiles : fallbackProfiles).map((profile) => [profile.id, profile]));
    return profileOrder.map((id) => byId.get(id) || { id, description: "" });
  }, [profiles]);
  const availableAgents = useMemo(
    () => agentsData?.agents.map((agent) => agent.id) || ["codex", "claude", "gemini"],
    [agentsData]
  );
  const selectedSpec = draftSpec;
  const projectName = projectNameFromPath(projectPath);
  const yamlPreview = useMemo(
    () => yamlForTemplate(selectedSpec, projectName, availableAgents),
    [selectedSpec, projectName, availableAgents]
  );

  useEffect(() => {
    if (!isOpen) return;
    if (!visibleProfiles.some((profile) => profile.id === selectedProfileId)) {
      const nextId = visibleProfiles[0]?.id || defaultProfileId;
      setSelectedProfileId(nextId);
      setDraftSpec(cloneTemplate(templateSpecs[nextId] || templateSpecs[defaultProfileId]));
    }
  }, [isOpen, selectedProfileId, visibleProfiles]);

  useEffect(() => {
    if (isOpen) return;
    setStep("select");
    setSelectedProfileId(defaultProfileId);
    setDraftSpec(cloneTemplate(templateSpecs[defaultProfileId]));
  }, [isOpen]);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key !== "Tab" || !modalRef.current) return;
      const focusable = modalRef.current.querySelectorAll<HTMLElement>(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else if (document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", handleKey);
    const timer = setTimeout(() => {
      const focusable = modalRef.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
      );
      focusable?.[0]?.focus();
    }, 50);
    return () => {
      document.removeEventListener("keydown", handleKey);
      clearTimeout(timer);
    };
  }, [isOpen]);

  const handleCreate = useCallback(async () => {
    try {
      await saveMutation.mutateAsync({ content: yamlPreview, scope });
      setStep("done");
      toast.success(t("configSaved"));
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
      closeTimerRef.current = setTimeout(() => {
        onCreated();
        onClose();
      }, 900);
    } catch (e: unknown) {
      toast.error(String(e));
    }
  }, [saveMutation, yamlPreview, scope, toast, t, onCreated, onClose]);

  const selectProfile = useCallback((profileId: string) => {
    setSelectedProfileId(profileId);
    setDraftSpec(cloneTemplate(templateSpecs[profileId] || templateSpecs[defaultProfileId]));
  }, []);

  const updateTabName = useCallback((tabIndex: number, name: string) => {
    setDraftSpec((prev) => ({
      ...prev,
      tabs: prev.tabs.map((tab, index) => index === tabIndex ? { ...tab, name } : tab),
    }));
  }, []);

  const updatePaneName = useCallback((tabIndex: number, paneIndex: number, name: string) => {
    setDraftSpec((prev) => ({
      ...prev,
      tabs: prev.tabs.map((tab, index) => index === tabIndex
        ? {
            ...tab,
            panes: tab.panes.map((pane, currentPaneIndex) => currentPaneIndex === paneIndex ? { ...pane, name } : pane),
          }
        : tab
      ),
    }));
  }, []);

  const updatePaneAgent = useCallback((tabIndex: number, paneIndex: number, agent: string) => {
    setDraftSpec((prev) => ({
      ...prev,
      tabs: prev.tabs.map((tab, index) => index === tabIndex
        ? {
            ...tab,
            panes: tab.panes.map((pane, currentPaneIndex) => currentPaneIndex === paneIndex ? { ...pane, agent } : pane),
          }
        : tab
      ),
    }));
  }, []);

  if (!isOpen) return null;

  const stepTitle = step === "select" ? t("createWorkspace") : t("done");

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center p-3 sm:p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget && step !== "done") onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <button
        type="button"
        className="absolute inset-0 w-full h-full bg-black/20 backdrop-blur-sm animate-fade-in cursor-default"
        onClick={() => {
          if (step !== "done") onClose();
        }}
        aria-hidden="true"
        tabIndex={-1}
      />
      <div ref={modalRef} className="relative z-10 w-[min(1060px,calc(100vw-2rem))] h-[min(700px,92dvh)] surface-card border border-default rounded-lg animate-modal-in overflow-hidden flex flex-col">
        <div className="px-4 sm:px-5 py-3 border-b border-default flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-[var(--accent-border)] bg-[var(--accent-bg)]">
              <Wand2 className="w-4 h-4 text-[var(--accent)]" />
            </span>
            <div className="min-w-0">
              <h3 id={titleId} className="text-sm font-semibold text-primary">{stepTitle}</h3>
              <p className="mt-0.5 truncate text-[11px] text-tertiary">{t("createWorkspaceDesc", { project: projectName })}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-7 h-7 rounded flex items-center justify-center text-tertiary hover:text-primary hover:surface-hover transition-colors"
            aria-label={t("cancel")}
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {step === "select" && (
            <div className="grid min-h-full min-w-0 lg:grid-cols-[280px_minmax(0,1fr)]">
              <div className="min-w-0 overflow-hidden border-b lg:border-b-0 lg:border-r border-default bg-[var(--bg-elevated)]/45 p-3 sm:p-4">
                <p className="text-[12px] font-semibold text-primary">{t("chooseTemplate")}</p>
                <p className="mt-1 text-[11px] leading-5 text-secondary">{t("chooseTemplateDesc")}</p>
                <div className="mt-3 grid gap-2">
                  {visibleProfiles.map((profile) => {
                    const selected = selectedProfileId === profile.id;
                    const spec = templateSpecs[profile.id];
                    const stats = spec ? templateStats(spec) : null;
                    return (
                      <button
                        type="button"
                        key={profile.id}
                        onClick={() => selectProfile(profile.id)}
                        className={`w-full min-w-0 overflow-hidden text-left px-3 py-2.5 rounded-md border transition-colors flex items-start gap-3 ${
                          selected
                            ? "border-[var(--accent-border)] bg-[var(--accent-bg)]"
                            : "border-default bg-[var(--bg-card)] hover:surface-hover"
                        }`}
                      >
                        <div className="w-8 h-8 rounded bg-[var(--bg-card)] border border-default flex items-center justify-center shrink-0 text-[var(--accent)]">
                          {profileIcons[profile.id] || <Zap className="w-4 h-4" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[13px] font-semibold text-primary">
                            {t(profileLabelKeys[profile.id] || profile.id)}
                          </p>
                          <p className="mt-0.5 text-[11px] leading-4 text-secondary">
                            {profileDescriptionKeys[profile.id] ? t(profileDescriptionKeys[profile.id]) : profile.description}
                          </p>
                          {spec && (
                            <span className="mt-2 flex flex-wrap items-center gap-1.5">
                              <span className="rounded border border-default bg-[var(--bg-elevated)] px-1.5 py-0.5 text-[10px] font-semibold text-tertiary">
                                {t("templateTabsPanes", { tabs: stats?.tabs || 0, panes: stats?.panes || 0 })}
                              </span>
                              <span className="rounded border border-default bg-[var(--bg-elevated)] px-1.5 py-0.5 text-[10px] font-semibold text-tertiary">
                                {stats?.directTabs ? t("templateMixedRuntime") : t("templateTmuxRuntime")}
                              </span>
                            </span>
                          )}
                        </div>
                        {selected && <CheckCircle2 className="w-3.5 h-3.5 text-[var(--accent)]" />}
                      </button>
                    );
                  })}
                  {!profiles && (
                    <div className="flex items-center justify-center py-5">
                      <Loader2 className="w-5 h-5 text-tertiary animate-spin" />
                    </div>
                  )}
                </div>
              </div>

              <div className="flex min-h-full min-w-0 flex-col p-3 sm:p-4">
                <div className="mb-3 rounded-lg border border-default bg-[var(--bg-card)] px-3 py-2.5">
                  <p className="text-[10px] font-semibold uppercase text-tertiary">{t("workspace")}</p>
                  <p className="mt-1 text-[14px] font-semibold text-primary truncate">{projectName}</p>
                </div>

                <div className="min-h-0 flex-1">
                  <section className="rounded-lg border border-default bg-[var(--bg-elevated)] p-3">
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <div>
                        <h4 className="text-[12px] font-semibold text-primary">{t("livePreview")}</h4>
                        <p className="mt-0.5 text-[11px] text-tertiary">{t("livePreviewDesc")}</p>
                      </div>
                    </div>
                    <WorkspacePreview
                      spec={selectedSpec}
                      availableAgents={availableAgents}
                      onRenameTab={updateTabName}
                      onRenamePane={updatePaneName}
                      onChangeAgent={updatePaneAgent}
                    />
                  </section>
                </div>

                <div className="mt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-md border border-default bg-[var(--bg-card)] px-3 py-2.5">
                  <div className="min-w-0 grid gap-1">
                    <p className="text-[11px] font-semibold text-primary">{t("templateCreateHint")}</p>
                  </div>
                  <div className="flex items-center justify-end gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={onClose}
                      className="control-touch px-3 rounded-md text-[13px] font-medium text-secondary hover:text-primary surface-hover transition-colors"
                    >
                      {t("cancel")}
                    </button>
                    <button
                      type="button"
                      onClick={handleCreate}
                      disabled={saveMutation.isPending}
                      className="control-touch px-3 rounded-md text-[13px] font-semibold bg-[var(--accent)] text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                      {saveMutation.isPending ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Save className="w-3.5 h-3.5" />
                      )}
                      {t("createSelectedTemplate")}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === "done" && (
            <div className="text-center py-8 space-y-3">
              <div className="w-10 h-10 rounded-lg success-bg flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-5 h-5 text-[var(--success)]" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-primary">{t("configSaved")}</h4>
                <p className="text-[11px] text-secondary mt-1">{t("refreshing")}…</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
                  onCreated();
                  onClose();
                }}
                className="h-8 px-4 rounded text-[13px] font-medium bg-[var(--accent)] text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors"
              >
                {t("manualClose")}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
