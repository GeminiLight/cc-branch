import { useState } from "react";
import {
  ArrowRight,
  GitBranch,
  RefreshCw,
  Wand2,
} from "lucide-react";
import { useI18n } from "../i18n";
import ConfigWizard from "./ConfigWizard";

interface SetupGuideProps {
  projectPath?: string;
  onRefresh?: () => void;
}

export default function SetupGuide({ projectPath, onRefresh }: SetupGuideProps) {
  const { t } = useI18n();
  const [wizardOpen, setWizardOpen] = useState(false);
  const projectName = projectPath?.split(/[\\/]/).filter(Boolean).pop() || t("project");

  const previewLanes = [
    { name: "planner", agent: "codex", tone: "accent" },
    { name: "builder", agent: "codex", tone: "success" },
    { name: "tester", agent: "codex", tone: "warning" },
    { name: "reviewer", agent: "claude", tone: "neutral" },
  ];

  return (
    <div className="page-shell py-5 sm:py-7">
      <section className="onboarding-hero overflow-hidden rounded-lg border border-default shadow-sm">
        <div className="grid min-h-[520px] lg:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)]">
          <div className="px-5 py-5 sm:px-7 sm:py-7 lg:px-8 lg:py-8 flex flex-col">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-md border border-[var(--accent-border)] bg-[var(--accent-bg)] px-2.5 py-1 text-[11px] font-semibold text-[var(--accent)]">
                <GitBranch className="w-3 h-3" />
                {t("onboardingEyebrow")}
              </span>
              <span className="inline-flex items-center rounded-md border border-default bg-[var(--bg-card)]/70 px-2.5 py-1 text-[11px] font-medium text-tertiary">
                {t("onboardingStatus")}
              </span>
            </div>

            <div className="mt-7 max-w-[580px]">
              <h1 className="text-[30px] sm:text-[38px] leading-[1.08] font-semibold tracking-tight text-primary">
                {t("noConfigTitle", { project: projectName })}
              </h1>
              <p className="mt-4 text-[15px] leading-7 text-secondary max-w-[42ch]">
                {t("noConfigDesc")}
              </p>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] items-stretch">
              <div className="rounded-md border border-default bg-[var(--bg-card)]/72 px-3.5 py-3 min-w-0">
                <p className="text-[10px] font-semibold uppercase text-tertiary">{t("projectDirectory")}</p>
                <p className="mt-1 truncate font-mono text-[12px] text-primary" title={projectPath}>
                  {projectPath || t("current")}
                </p>
              </div>
              <div className="rounded-md border border-[var(--success)]/20 bg-[var(--success-bg)] px-3.5 py-3 min-w-[160px]">
                <p className="text-[10px] font-semibold uppercase text-tertiary">{t("setupNextOutcome")}</p>
                <p className="mt-1 text-[12px] font-semibold text-primary">{t("configuration")}</p>
              </div>
            </div>

            <div className="mt-6 flex flex-col sm:flex-row gap-2.5">
              <button
                type="button"
                onClick={() => setWizardOpen(true)}
                className="control-touch inline-flex items-center justify-center gap-2 rounded-md bg-[var(--accent)] px-5 text-[13px] font-semibold text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors shadow-sm"
              >
                <Wand2 className="w-4 h-4" />
                {t("createConfigInteractively")}
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => onRefresh?.()}
                disabled={!onRefresh}
                className="control-touch inline-flex items-center justify-center gap-1.5 rounded-md border border-default bg-[var(--bg-card)]/72 px-3.5 text-[13px] font-medium text-secondary hover:text-primary hover:bg-[var(--bg-hover)] transition-colors disabled:opacity-50"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                {t("refresh")}
              </button>
            </div>
          </div>

          <div className="border-t lg:border-t-0 lg:border-l border-default bg-[var(--bg-card)]/58 px-4 py-5 sm:px-6 sm:py-7">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase text-tertiary">{t("onboardingMapEyebrow")}</p>
                <h2 className="mt-1 text-[16px] font-semibold text-primary">{t("onboardingMapTitle")}</h2>
              </div>
            </div>

            <div className="mt-5 rounded-lg border border-default bg-[var(--editor-bg)] p-3.5 shadow-sm">
              <div className="flex items-center gap-1.5 border-b border-default pb-3">
                <span className="h-2.5 w-2.5 rounded-full bg-[#d4574f]" />
                <span className="h-2.5 w-2.5 rounded-full bg-[#d9a338]" />
                <span className="h-2.5 w-2.5 rounded-full bg-[#3e9f75]" />
                <span className="ml-2 truncate font-mono text-[10px] text-tertiary">
                  cc-branch / {projectName}
                </span>
              </div>

              <div className="mt-3 grid gap-2">
                {previewLanes.map((lane) => (
                  <div
                    key={lane.name}
                    className="grid grid-cols-[82px_minmax(0,1fr)_auto] items-center gap-2 rounded-md border border-default bg-[var(--bg-card)] px-2.5 py-2"
                  >
                    <span className="font-mono text-[11px] font-semibold text-primary">{lane.name}</span>
                    <div className="h-1.5 rounded-full bg-[var(--border-subtle)] overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          lane.tone === "success"
                            ? "bg-[var(--success)]"
                            : lane.tone === "warning"
                              ? "bg-[var(--warning)]"
                              : lane.tone === "neutral"
                                ? "bg-[var(--text-muted)]"
                                : "bg-[var(--accent)]"
                        }`}
                        style={{ width: lane.name === "reviewer" ? "58%" : "74%" }}
                      />
                    </div>
                    <span className="rounded border border-default bg-[var(--bg-elevated)] px-1.5 py-0.5 font-mono text-[10px] text-secondary">
                      {lane.agent}
                    </span>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      </section>

      <ConfigWizard
        projectPath={projectPath}
        isOpen={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onCreated={() => {
          setWizardOpen(false);
          onRefresh?.();
        }}
      />
    </div>
  );
}
