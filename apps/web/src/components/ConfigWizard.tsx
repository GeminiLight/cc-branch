import { useRef, useState, useCallback, useId, useEffect } from "react";
import {
  Loader2,
  Wand2,
  User,
  Users,
  Minimize2,
  CheckCircle2,
  Pencil,
  Save,
  X,
  Zap,
  ChevronRight,
} from "lucide-react";
import { useI18n } from "../i18n";
import { useToast } from "./ui/Toast";
import { useApiClient, useProfiles, useInitWorkspace, useConfig, useSaveConfig } from "../hooks";
import Prism from "prismjs";
import "prismjs/components/prism-yaml";

interface ConfigWizardProps {
  projectPath?: string;
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

type Step = "select" | "preview" | "done";

const profileIcons: Record<string, React.ReactNode> = {
  "solo-dev": <User className="w-4 h-4" />,
  "ai-pair": <Users className="w-4 h-4" />,
  minimal: <Minimize2 className="w-4 h-4" />,
};

export default function ConfigWizard({ projectPath, isOpen, onClose, onCreated }: ConfigWizardProps) {
  const api = useApiClient();
  const { t } = useI18n();
  const toast = useToast();
  const { data: profiles } = useProfiles();
  const initMutation = useInitWorkspace();
  const { data: configData } = useConfig(projectPath);
  const saveMutation = useSaveConfig();

  const [step, setStep] = useState<Step>("select");
  const [configContent, setConfigContent] = useState("");
  const [editing, setEditing] = useState(false);
  const codeRef = useRef<HTMLElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const titleId = useId();

  useEffect(() => {
    if (isOpen) return;
    setStep("select");
    setConfigContent("");
    setEditing(false);
  }, [isOpen]);

  useEffect(() => {
    if (codeRef.current && configContent && !editing) {
      Prism.highlightElement(codeRef.current);
    }
  }, [configContent, editing]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    };
  }, []);

  // Focus trap
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
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", handleKey);
    // Auto-focus
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

  const handleSelect = useCallback(async (profileId: string) => {
    try {
      await initMutation.mutateAsync({ profile: profileId, bootstrapSessions: true, projectPath });
      const cfg = await api.getConfig(projectPath);
      setConfigContent(cfg.content);
      setStep("preview");
      toast.success(t("configSaved"));
    } catch (e: unknown) {
      toast.error(String(e));
    }
  }, [initMutation, api, projectPath, toast, t]);

  const handleSave = useCallback(async () => {
    try {
      await saveMutation.mutateAsync({ content: configContent, projectPath });
      setStep("done");
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
      closeTimerRef.current = setTimeout(() => {
        onCreated();
        onClose();
      }, 1200);
    } catch (e: unknown) {
      toast.error(String(e));
    }
  }, [saveMutation, configContent, projectPath, onClose, onCreated, toast]);

  if (!isOpen) return null;

  const stepTitle =
    step === "select" ? t("createConfig") : step === "preview" ? t("review") : t("done");

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center p-4"
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
      <div ref={modalRef} className="relative z-10 w-full max-w-lg surface-card border border-default rounded-lg animate-modal-in overflow-hidden">
        <div className="px-5 py-3 border-b border-default flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wand2 className="w-4 h-4 text-[var(--accent)]" />
            <h3 id={titleId} className="text-sm font-semibold text-primary">{stepTitle}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-6 h-6 rounded flex items-center justify-center text-tertiary hover:text-primary hover:surface-hover transition-colors"
            aria-label={t("cancel")}
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="px-5 py-4">
          {step === "select" && (
            <div className="space-y-3">
              <p className="text-[13px] text-secondary">{t("chooseTemplate")}</p>
              <div className="space-y-1.5">
                {profiles?.map((p) => (
                  <button
                    type="button"
                    key={p.id}
                    onClick={() => handleSelect(p.id)}
                    disabled={initMutation.isPending}
                    className="w-full text-left px-3 py-2.5 rounded-md border border-default surface-card hover:surface-hover transition-colors flex items-center gap-3 group"
                  >
                    <div className="w-8 h-8 rounded bg-[var(--accent-bg)] flex items-center justify-center shrink-0 text-[var(--accent)]">
                      {profileIcons[p.id] || <Zap className="w-4 h-4" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-semibold text-primary capitalize">
                        {p.id.replace("-", " ")}
                      </p>
                      <p className="text-[11px] text-secondary">{p.description}</p>
                    </div>
                    {initMutation.isPending ? (
                      <Loader2 className="w-3.5 h-3.5 text-tertiary animate-spin" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-tertiary opacity-0 group-hover:opacity-100 transition-opacity" />
                    )}
                  </button>
                ))}
                {!profiles && (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-5 h-5 text-tertiary animate-spin" />
                  </div>
                )}
              </div>
            </div>
          )}

          {step === "preview" && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 p-2.5 rounded success-bg border border-[var(--success)]/10">
                <CheckCircle2 className="w-4 h-4 text-[var(--success)] shrink-0" />
                <div>
                  <p className="text-[13px] font-semibold text-primary">
                    {configData?.path.split("/").pop() || ".cc-branch.yaml"}
                  </p>
                </div>
              </div>

              <div className="border border-default rounded overflow-hidden">
                <div className="px-3 py-1.5 border-b border-default flex items-center justify-between bg-[var(--bg-hover)]">
                  <span className="text-[10px] font-semibold text-tertiary uppercase tracking-wide">
                    .cc-branch.yaml
                  </span>
                  <button
                    type="button"
                    onClick={() => setEditing((e) => !e)}
                    className="h-6 px-2 rounded text-[11px] font-medium text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center gap-1"
                  >
                    <Pencil className="w-3 h-3" />
                    {editing ? t("preview") : t("edit")}
                  </button>
                </div>
                {editing ? (
                  <textarea
                    value={configContent}
                    onChange={(e) => setConfigContent(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Tab") {
                        e.preventDefault();
                        const target = e.target as HTMLTextAreaElement;
                        const start = target.selectionStart;
                        const end = target.selectionEnd;
                        const newValue = configContent.substring(0, start) + "  " + configContent.substring(end);
                        setConfigContent(newValue);
                        requestAnimationFrame(() => {
                          target.selectionStart = target.selectionEnd = start + 2;
                        });
                      }
                    }}
                    className="w-full h-56 p-3 text-[12px] font-mono text-[var(--editor-fg)] bg-[var(--editor-bg)] resize-none focus:outline-none"
                    spellCheck={false}
                    aria-label=".cc-branch.yaml"
                  />
                ) : (
                  <pre className="language-yaml !rounded-none !border-0 !m-0 max-h-56 overflow-auto">
                    <code ref={codeRef} className="language-yaml">
                      {configContent}
                    </code>
                  </pre>
                )}
              </div>

              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="h-8 px-3 rounded text-[13px] font-medium text-secondary hover:text-primary surface-hover transition-colors"
                >
                  {t("cancel")}
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saveMutation.isPending}
                  className="h-8 px-3 rounded text-[13px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saveMutation.isPending ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Save className="w-3.5 h-3.5" />
                  )}
                  {t("save")}
                </button>
              </div>
            </div>
          )}

          {step === "done" && (
            <div className="text-center py-6 space-y-3">
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
                className="h-8 px-4 rounded text-[13px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
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
