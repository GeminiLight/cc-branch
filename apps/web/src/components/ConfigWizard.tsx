import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import {
  CheckCircle2,
  Code2,
  GitBranch,
  Loader2,
  Minimize2,
  Monitor,
  Save,
  User,
  Users,
  Wand2,
  X,
  Zap,
} from "lucide-react";
import { useI18n } from "../i18n";
import { useToast } from "./ui/Toast";
import { useAgents, useInitWorkspace, useProfiles } from "../hooks";
import type { Profile } from "../types";

interface ConfigWizardProps {
  projectPath?: string;
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

type Step = "select" | "done";

interface PreviewWindow {
  name: string;
  preferredAgents: string[];
}

interface PreviewSlot {
  name: string;
  runtime: "tmux" | "terminal";
  windows: PreviewWindow[];
}

interface TemplateSpec {
  id: string;
  slots: PreviewSlot[];
}

const profileIcons: Record<string, React.ReactNode> = {
  "solo-dev": <User className="w-4 h-4" />,
  "ai-pair": <Users className="w-4 h-4" />,
  minimal: <Minimize2 className="w-4 h-4" />,
};

const profileLabelKeys: Record<string, string> = {
  "solo-dev": "profileSoloDevName",
  "ai-pair": "profileAiPairName",
  minimal: "profileMinimalName",
};

const profileDescriptionKeys: Record<string, string> = {
  "solo-dev": "profileSoloDevDesc",
  "ai-pair": "profileAiPairDesc",
  minimal: "profileMinimalDesc",
};

const templateSpecs: Record<string, TemplateSpec> = {
  "solo-dev": {
    id: "solo-dev",
    slots: [
      {
        name: "dev",
        runtime: "tmux",
        windows: [
          { name: "planner", preferredAgents: ["codex", "claude", "gemini"] },
          { name: "builder", preferredAgents: ["codex", "claude", "gemini"] },
          { name: "review", preferredAgents: ["claude", "codex", "gemini"] },
        ],
      },
      { name: "scratch", runtime: "terminal", windows: [] },
    ],
  },
  "ai-pair": {
    id: "ai-pair",
    slots: [
      {
        name: "coder",
        runtime: "tmux",
        windows: [{ name: "implement", preferredAgents: ["codex", "claude", "gemini"] }],
      },
      {
        name: "reviewer",
        runtime: "tmux",
        windows: [{ name: "review", preferredAgents: ["claude", "codex", "gemini"] }],
      },
      { name: "scratch", runtime: "terminal", windows: [] },
    ],
  },
  minimal: {
    id: "minimal",
    slots: [
      {
        name: "main",
        runtime: "tmux",
        windows: [{ name: "agent", preferredAgents: ["claude", "codex", "gemini"] }],
      },
      { name: "scratch", runtime: "terminal", windows: [] },
    ],
  },
};

const fallbackProfiles: Profile[] = [
  { id: "solo-dev", description: "" },
  { id: "ai-pair", description: "" },
  { id: "minimal", description: "" },
];

function projectNameFromPath(projectPath?: string): string {
  return projectPath?.split(/[\\/]/).filter(Boolean).pop() || "workspace";
}

function agentForWindow(win: PreviewWindow, availableAgents: string[]): string {
  return win.preferredAgents.find((agent) => availableAgents.includes(agent)) || win.preferredAgents[0] || "shell";
}

function yamlForTemplate(spec: TemplateSpec, projectName: string, availableAgents: string[]): string {
  const lines = [
    "version: 1",
    `project: "${projectName}"`,
    'root: "."',
    "",
    "display:",
    '  mode: "grid"',
    "  columns: 2",
    "  dashboard: true",
    "",
    "slots:",
  ];

  for (const slot of spec.slots) {
    lines.push(`  - name: "${slot.name}"`);
    lines.push(`    runtime: "${slot.runtime}"`);
    lines.push('    cwd: "."');

    if (slot.runtime === "terminal") {
      lines.push('    title: "scratch"');
      lines.push('    command: "$SHELL"');
      continue;
    }

    lines.push("    windows:");
    for (const win of slot.windows) {
      lines.push(`      - name: "${win.name}"`);
      lines.push(`        agent: "${agentForWindow(win, availableAgents)}"`);
    }
  }

  return lines.join("\n");
}

function WorkspacePreview({
  spec,
  availableAgents,
}: {
  spec: TemplateSpec;
  availableAgents: string[];
}) {
  const { t } = useI18n();
  return (
    <div className="space-y-2">
      {spec.slots.map((slot) => (
        <div key={slot.name} className="rounded-md border border-default bg-[var(--bg-card)] p-2.5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <Monitor className="w-3.5 h-3.5 text-[var(--accent)] shrink-0" />
              <span className="font-mono text-[12px] font-semibold text-primary truncate">{slot.name}</span>
            </div>
            <span className="rounded border border-default bg-[var(--bg-elevated)] px-1.5 py-0.5 text-[10px] font-mono text-tertiary">
              {slot.runtime}
            </span>
          </div>

          {slot.runtime === "terminal" ? (
            <div className="mt-2 rounded border border-dashed border-default px-2 py-1.5 text-[11px] text-secondary">
              scratch shell
            </div>
          ) : (
            <div className="mt-2 grid gap-1.5">
              {slot.windows.map((win) => (
                <div
                  key={win.name}
                  className="grid grid-cols-[minmax(72px,0.9fr)_minmax(0,1.2fr)_auto] items-center gap-2 rounded border border-default bg-[var(--bg-elevated)] px-2 py-1.5"
                >
                  <span className="font-mono text-[11px] text-primary truncate">{win.name}</span>
                  <span className="h-1.5 rounded-full bg-[var(--accent)]/80" />
                  <span className="rounded bg-[var(--accent-bg)] px-1.5 py-0.5 text-[10px] font-mono text-[var(--accent)]">
                    {agentForWindow(win, availableAgents)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
      <div className="flex items-center gap-2 text-[11px] text-tertiary">
        <GitBranch className="w-3.5 h-3.5" />
        <span>{t("templatePreviewSync")}</span>
      </div>
    </div>
  );
}

export default function ConfigWizard({ projectPath, isOpen, onClose, onCreated }: ConfigWizardProps) {
  const { t } = useI18n();
  const toast = useToast();
  const { data: profiles } = useProfiles();
  const { data: agentsData } = useAgents(projectPath, isOpen);
  const initMutation = useInitWorkspace();

  const [step, setStep] = useState<Step>("select");
  const [selectedProfileId, setSelectedProfileId] = useState("solo-dev");
  const modalRef = useRef<HTMLDivElement>(null);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const titleId = useId();

  const visibleProfiles = profiles?.length ? profiles : fallbackProfiles;
  const availableAgents = useMemo(
    () => agentsData?.agents.map((agent) => agent.id) || ["codex", "claude", "gemini"],
    [agentsData]
  );
  const selectedSpec = templateSpecs[selectedProfileId] || templateSpecs["solo-dev"];
  const projectName = projectNameFromPath(projectPath);
  const yamlPreview = useMemo(
    () => yamlForTemplate(selectedSpec, projectName, availableAgents),
    [selectedSpec, projectName, availableAgents]
  );

  useEffect(() => {
    if (!isOpen) return;
    if (!visibleProfiles.some((profile) => profile.id === selectedProfileId)) {
      setSelectedProfileId(visibleProfiles[0]?.id || "solo-dev");
    }
  }, [isOpen, selectedProfileId, visibleProfiles]);

  useEffect(() => {
    if (isOpen) return;
    setStep("select");
    setSelectedProfileId("solo-dev");
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
      await initMutation.mutateAsync({ profile: selectedProfileId, bootstrapSessions: true, projectPath });
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
  }, [initMutation, selectedProfileId, projectPath, toast, t, onCreated, onClose]);

  if (!isOpen) return null;

  const stepTitle = step === "select" ? t("createConfig") : t("done");

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
      <div ref={modalRef} className="relative z-10 w-full max-w-5xl max-h-[92dvh] surface-card border border-default rounded-lg animate-modal-in overflow-hidden flex flex-col">
        <div className="px-4 sm:px-5 py-3 border-b border-default flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <Wand2 className="w-4 h-4 text-[var(--accent)]" />
            <h3 id={titleId} className="text-sm font-semibold text-primary">{stepTitle}</h3>
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

        <div className="overflow-y-auto">
          {step === "select" && (
            <div className="grid lg:grid-cols-[280px_minmax(0,1fr)]">
              <div className="border-b lg:border-b-0 lg:border-r border-default p-3 sm:p-4">
                <p className="text-[12px] font-medium text-secondary">{t("chooseTemplate")}</p>
                <div className="mt-3 space-y-1.5">
                  {visibleProfiles.map((profile) => {
                    const selected = selectedProfileId === profile.id;
                    return (
                      <button
                        type="button"
                        key={profile.id}
                        onClick={() => setSelectedProfileId(profile.id)}
                        className={`w-full text-left px-3 py-2.5 rounded-md border transition-colors flex items-center gap-3 ${
                          selected
                            ? "border-[var(--accent-border)] bg-[var(--accent-bg)]"
                            : "border-default hover:surface-hover"
                        }`}
                      >
                        <div className="w-8 h-8 rounded bg-[var(--bg-card)] border border-default flex items-center justify-center shrink-0 text-[var(--accent)]">
                          {profileIcons[profile.id] || <Zap className="w-4 h-4" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[13px] font-semibold text-primary">
                            {t(profileLabelKeys[profile.id] || profile.id)}
                          </p>
                          <p className="text-[11px] text-secondary truncate">
                            {profileDescriptionKeys[profile.id] ? t(profileDescriptionKeys[profile.id]) : profile.description}
                          </p>
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

              <div className="p-3 sm:p-4 space-y-3">
                <div className="grid xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.86fr)] gap-3">
                  <section className="rounded-lg border border-default bg-[var(--bg-elevated)] p-3">
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <h4 className="text-[12px] font-semibold text-primary">{t("livePreview")}</h4>
                      <span className="text-[10px] font-mono text-tertiary">
                        {selectedSpec.slots.length} {t("slotsTitle").toLowerCase()}
                      </span>
                    </div>
                    <WorkspacePreview spec={selectedSpec} availableAgents={availableAgents} />
                  </section>

                  <section className="rounded-lg border border-default overflow-hidden bg-[var(--editor-bg)]">
                    <div className="px-3 py-2 border-b border-default flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <Code2 className="w-3.5 h-3.5 text-[var(--accent)]" />
                        <span className="text-[11px] font-semibold text-primary">config.yaml</span>
                      </div>
                      <span className="text-[10px] text-tertiary">{t("templateWillWrite")}</span>
                    </div>
                    <pre className="m-0 max-h-[360px] overflow-auto px-3 py-3 text-[11px] leading-5 text-[var(--editor-fg)]">
                      <code>{yamlPreview}</code>
                    </pre>
                  </section>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-md border border-default bg-[var(--bg-card)] px-3 py-2.5">
                  <div className="min-w-0">
                    <p className="text-[11px] font-semibold text-primary">{t("templateCreateHint")}</p>
                    <p className="text-[10px] text-tertiary truncate" title={projectPath}>
                      {projectPath || t("current")}
                    </p>
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
                      disabled={initMutation.isPending}
                      className="control-touch px-3 rounded-md text-[13px] font-semibold bg-[var(--accent)] text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                      {initMutation.isPending ? (
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
