import { useState } from "react";
import {
  ChevronRight,
  FileText,
  RefreshCw,
  Rocket,
  Settings,
  Terminal,
  Wand2,
} from "lucide-react";
import { useI18n } from "../i18n";
import ConfigWizard from "./ConfigWizard";

interface SetupGuideProps {
  projectPath?: string;
  onRefresh?: () => void;
}

interface StepWithCode {
  icon: typeof Terminal;
  title: string;
  desc: string;
  code: string;
  tip?: string;
  previewItems?: never;
}

interface StepWithPreview {
  icon: typeof Settings;
  title: string;
  desc: string;
  code: string;
  previewItems: { label: string; desc: string }[];
  tip?: never;
}

type Step = StepWithCode | StepWithPreview;

export default function SetupGuide({ projectPath, onRefresh }: SetupGuideProps) {
  const { t } = useI18n();
  const [wizardOpen, setWizardOpen] = useState(false);

  const steps: Step[] = [
    {
      icon: Wand2,
      title: t("step1Title"),
      desc: t("step1Desc"),
      code: t("step1Code"),
      tip: t("step1Tip"),
    },
    {
      icon: Settings,
      title: t("step2Title"),
      desc: t("step2Desc"),
      code: `slots:\n  - name: "dev"\n    backend: "tmux"\n    windows:\n      - name: "planner"\n        agent: "claude"`,
      previewItems: [
        { label: "slots", desc: t("step2Slots") },
        { label: "agents", desc: t("step2Agents") },
        { label: "windows", desc: t("step2Windows") },
      ],
    },
    {
      icon: Rocket,
      title: t("step3Title"),
      desc: t("step3Desc"),
      code: "cc-branch start",
      tip: t("step3Tip"),
    },
  ];

  return (
    <div className="max-w-md mx-auto py-12 px-4">
      <div className="text-center mb-8">
        <div className="w-10 h-10 rounded-lg bg-[var(--accent-bg)] mx-auto mb-3 flex items-center justify-center">
          <Settings className="w-5 h-5 text-[var(--accent)]" />
        </div>
        <h1 className="text-lg font-semibold text-primary tracking-tight">
          {t("noConfigTitle")}
        </h1>
        <p className="text-[13px] text-secondary mt-1">{t("noConfigDesc")}</p>
        <button
          type="button"
          onClick={() => setWizardOpen(true)}
          className="mt-4 inline-flex items-center gap-1.5 h-8 px-4 rounded text-[13px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
        >
          <Wand2 className="w-3.5 h-3.5" />
          {t("createConfigInteractively")}
        </button>
      </div>

      <div className="space-y-2">
        {steps.map((step, i) => (
          <div
            key={i}
            className="surface-card border border-default rounded-lg overflow-hidden"
          >
            <div className="px-4 py-3 flex items-start gap-3">
              <div className="w-7 h-7 rounded bg-[var(--accent-bg)] flex items-center justify-center shrink-0 mt-px">
                <step.icon className="w-3.5 h-3.5 text-[var(--accent)]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-bold text-[var(--accent)]">
                    {t("step")} {i + 1}
                  </span>
                  <ChevronRight className="w-3 h-3 text-tertiary" />
                </div>
                <h3 className="text-[13px] font-semibold text-primary mt-px">
                  {step.title}
                </h3>
                <p className="text-[11px] text-secondary mt-0.5 leading-relaxed">
                  {step.desc}
                </p>
                {step.code && (
                  <div className="mt-2 bg-[var(--editor-bg)] border border-[var(--editor-border)] rounded px-2.5 py-1.5">
                    <code className="text-[11px] font-mono text-[var(--editor-fg)] whitespace-pre-wrap">
                      {step.code}
                    </code>
                  </div>
                )}
                {"previewItems" in step && step.previewItems && (
                  <div className="mt-2 space-y-0.5">
                    {step.previewItems.map((item, j) => (
                      <div
                        key={j}
                        className="flex items-center gap-2 text-[11px] text-secondary bg-[var(--border-subtle)]/40 px-2 py-1 rounded"
                      >
                        <code className="text-[9px] font-mono text-[var(--accent)] font-semibold bg-[var(--accent-bg)] px-1 rounded">
                          {item.label}
                        </code>
                        <span>{item.desc}</span>
                      </div>
                    ))}
                  </div>
                )}
                {"tip" in step && step.tip && (
                  <p className="text-[11px] text-tertiary mt-1.5 flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    {step.tip}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {onRefresh && (
        <div className="text-center mt-5">
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex items-center gap-1.5 h-8 px-3 rounded text-[13px] font-medium surface-hover text-secondary hover:text-primary transition-colors border border-default"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            {t("refresh")}
          </button>
        </div>
      )}

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
