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
  configPath?: string;
  onRefresh?: () => void;
}

export default function SetupGuide({ projectPath, configPath, onRefresh }: SetupGuideProps) {
  const { t } = useI18n();
  const [wizardOpen, setWizardOpen] = useState(false);
  const projectName = projectPath?.split(/[\\/]/).filter(Boolean).pop() || t("project");
  const onboardingSteps = [t("profileDevelopmentName"), t("profileDesignName"), t("profileMinimalName")];

  return (
    <div className="page-shell py-4 sm:py-6">
      <section className="onboarding-hero overflow-hidden rounded-lg border border-default shadow-sm">
        <div className="grid min-h-[420px] lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="px-5 py-5 sm:px-7 sm:py-7 lg:px-8 lg:py-8 flex flex-col">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-md border border-[var(--accent-border)] bg-[var(--accent-bg)] px-2.5 py-1 text-[11px] font-semibold text-[var(--accent)]">
                <GitBranch className="w-3 h-3" />
                {t("onboardingEyebrow")}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-default bg-[var(--bg-card)]/70 px-2.5 py-1 text-[11px] font-medium text-tertiary">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--warning)]" aria-hidden="true" />
                {t("onboardingStatus")}
              </span>
            </div>

            <div className="mt-7 max-w-[640px]">
              <h1 className="text-[28px] sm:text-[36px] leading-[1.08] font-semibold tracking-tight text-primary">
                {t("noConfigTitle", { project: projectName })}
              </h1>
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              {onboardingSteps.map((step) => (
                <span key={step} className="rounded-md border border-default bg-[var(--bg-card)]/72 px-2.5 py-1 text-[12px] font-medium text-secondary">
                  {step}
                </span>
              ))}
            </div>

            <div className="mt-6 flex flex-col sm:flex-row gap-2.5">
              <button
                type="button"
                onClick={() => setWizardOpen(true)}
                className="control-touch inline-flex items-center justify-center gap-2 rounded-md bg-[var(--accent)] px-5 text-[13px] font-semibold text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors shadow-sm"
              >
                <Wand2 className="w-4 h-4" />
                {t("createWorkspaceInteractively")}
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

            <div className="mt-auto" />
          </div>

          <div className="border-t lg:border-t-0 lg:border-l border-default bg-[var(--bg-card)]/58 px-4 py-5 sm:px-6 sm:py-7">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase text-tertiary">{t("onboardingMapEyebrow")}</p>
                <h2 className="mt-1 text-[16px] font-semibold text-primary">{t("onboardingMapTitle")}</h2>
              </div>
            </div>

            <div className="mt-5 rounded-lg border border-default bg-[var(--bg-card)] p-3">
              <div className="rounded-md border border-[var(--accent-border)] bg-[var(--accent-bg)] px-3 py-2.5">
                <p className="text-[10px] font-semibold uppercase text-tertiary">{t("workspace")}</p>
                <p className="mt-1 text-[13px] font-semibold text-primary truncate">{projectName}</p>
              </div>
              <div className="ml-5 border-l border-default pl-3 pt-3">
                <div className="rounded-md border border-default bg-[var(--bg-elevated)] px-3 py-2.5">
                  <p className="text-[10px] font-semibold uppercase text-tertiary">{t("tab")}</p>
                  <p className="mt-1 text-[12px] font-semibold text-primary">{t("exampleTabName")}</p>
                </div>
                <div className="ml-5 border-l border-default pl-3 pt-3 grid gap-2">
                  <div className="rounded-md border border-default bg-[var(--bg-card)] px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase text-tertiary">{t("pane")}</p>
                    <p className="mt-1 text-[12px] font-semibold text-primary">frontend</p>
                  </div>
                  <div className="rounded-md border border-default bg-[var(--bg-card)] px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase text-tertiary">{t("pane")}</p>
                    <p className="mt-1 text-[12px] font-semibold text-primary">backend</p>
                  </div>
                  <div className="rounded-md border border-default bg-[var(--bg-card)] px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase text-tertiary">{t("pane")}</p>
                    <p className="mt-1 text-[12px] font-semibold text-primary">algorithm</p>
                  </div>
                  <div className="rounded-md border border-default bg-[var(--bg-card)] px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase text-tertiary">{t("pane")}</p>
                    <p className="mt-1 text-[12px] font-semibold text-primary">docs</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <ConfigWizard
        projectPath={projectPath}
        configPath={configPath}
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
