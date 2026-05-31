import { AppWindow, Bot, Check, Globe, Layers3, MonitorCog, Moon, Palette, ShieldCheck, Sun, type LucideIcon } from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";
import { useApiClient } from "../hooks";
import { useI18n, type Lang } from "../i18n";
import { useTheme, type Theme } from "../theme/ThemeProvider";
import DataLocationsSettings from "./DataLocationsSettings";
import DesktopUpdateSettings from "./DesktopUpdateSettings";
import GlobalAgentsSettings from "./GlobalAgentsSettings";
import GlobalOpenersSettings from "./GlobalOpenersSettings";
import TemplateCenterSettings from "./TemplateCenterSettings";
import Modal from "./ui/Modal";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const themeOptions: { value: Theme; labelKey: string; icon: typeof Sun }[] = [
  { value: "light", labelKey: "light", icon: Sun },
  { value: "dark", labelKey: "dark", icon: Moon },
];

const languageOptions: { value: Lang; label: string }[] = [
  { value: "en", label: "English" },
  { value: "zh", label: "中文" },
];

type SettingsPanel = "appearance" | "templates" | "openers" | "agents" | "maintenance";

const settingsPanels: { id: SettingsPanel; labelKey: string; icon: LucideIcon }[] = [
  { id: "appearance", labelKey: "settingsAppearance", icon: Palette },
  { id: "templates", labelKey: "settingsTemplates", icon: Layers3 },
  { id: "openers", labelKey: "settingsOpeners", icon: AppWindow },
  { id: "agents", labelKey: "settingsAgents", icon: Bot },
  { id: "maintenance", labelKey: "settingsMaintenance", icon: ShieldCheck },
];

function PreferenceGroup({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-default bg-[var(--bg-card)]">
      <div className="flex items-start gap-3 border-b border-subtle px-4 py-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--accent-border)] bg-[var(--accent-bg)]">
          <Icon className="h-4 w-4 text-[var(--accent)]" />
        </div>
        <div className="min-w-0">
          <h4 className="text-[13px] font-semibold text-primary">{title}</h4>
        </div>
      </div>
      <div className="px-4 py-3">{children}</div>
    </section>
  );
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { t, lang, setLang } = useI18n();
  const { theme, setTheme } = useTheme();
  const api = useApiClient();
  const [activePanel, setActivePanel] = useState<SettingsPanel>("appearance");

  const activePanelMeta = settingsPanels.find((panel) => panel.id === activePanel) ?? settingsPanels[0];
  const ActivePanelIcon = activePanelMeta.icon;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t("settings")}
      icon={<MonitorCog className="w-5 h-5 text-[var(--accent)]" />}
      size="lg"
    >
      <div className="grid h-[min(620px,calc(100dvh-9rem))] min-h-[420px] gap-4 md:grid-cols-[180px_minmax(0,1fr)]">
        <nav className="border-b border-subtle pb-3 md:border-b-0 md:border-r md:pb-0 md:pr-3" aria-label={t("settingsSections")}>
          <div className="grid grid-cols-2 gap-1 md:grid-cols-1">
            {settingsPanels.map(({ id, labelKey, icon: Icon }) => {
              const active = activePanel === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => setActivePanel(id)}
                  className={`min-h-12 rounded-lg px-2.5 py-2 text-left transition-colors ${
                    active
                      ? "border border-[var(--accent-border)] bg-[var(--accent-bg)] text-primary"
                      : "border border-transparent text-secondary hover:border-default hover:bg-[var(--bg-hover)] hover:text-primary"
                  }`}
                  aria-current={active ? "page" : undefined}
                >
                  <span className="flex items-center gap-2">
                    <Icon className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate text-[12px] font-semibold">{t(labelKey)}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </nav>

        <div className="flex min-h-0 min-w-0 flex-col">
          <div className="mb-3 shrink-0">
            <h3 className="mt-1 flex items-center gap-2 text-[14px] font-semibold text-primary">
              <ActivePanelIcon className="h-4 w-4 text-[var(--accent)]" />
              {t(activePanelMeta.labelKey)}
            </h3>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto pr-1">
          {activePanel === "appearance" && (
            <div className="space-y-3">
              <PreferenceGroup icon={Sun} title={t("themeSwitch")}>
                <div className="grid grid-cols-2 gap-2">
                  {themeOptions.map(({ value, labelKey, icon: Icon }) => {
                    const active = theme === value;
                    return (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setTheme(value)}
                        className={`control-touch rounded-md border px-3 text-[13px] font-medium flex items-center justify-between gap-2 transition-colors ${
                          active
                            ? "border-[var(--accent-border)] bg-[var(--accent-bg)] text-primary"
                            : "border-default text-secondary hover:text-primary hover:bg-[var(--bg-hover)]"
                        }`}
                        aria-pressed={active}
                      >
                        <span className="inline-flex items-center gap-2">
                          <Icon className="w-3.5 h-3.5" />
                          {t(labelKey)}
                        </span>
                        {active && <Check className="w-3.5 h-3.5 text-[var(--accent)]" />}
                      </button>
                    );
                  })}
                </div>
              </PreferenceGroup>

              <PreferenceGroup icon={Globe} title={t("langSwitch")}>
                <div className="grid grid-cols-2 gap-2">
                  {languageOptions.map(({ value, label }) => {
                    const active = lang === value;
                    return (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setLang(value)}
                        className={`control-touch rounded-md border px-3 text-[13px] font-medium flex items-center justify-between gap-2 transition-colors ${
                          active
                            ? "border-[var(--accent-border)] bg-[var(--accent-bg)] text-primary"
                            : "border-default text-secondary hover:text-primary hover:bg-[var(--bg-hover)]"
                        }`}
                        aria-pressed={active}
                      >
                        <span>{label}</span>
                        {active && <Check className="w-3.5 h-3.5 text-[var(--accent)]" />}
                      </button>
                    );
                  })}
                </div>
              </PreferenceGroup>
            </div>
          )}

          {activePanel === "templates" && <TemplateCenterSettings />}

          {activePanel === "maintenance" && (
            <div className="space-y-3">
              <DesktopUpdateSettings />
              <DataLocationsSettings />
            </div>
          )}

          {activePanel === "openers" && (
            <div className="rounded-lg border border-subtle bg-[var(--bg-card)] p-4">
              <GlobalOpenersSettings api={api} />
            </div>
          )}

          {activePanel === "agents" && (
            <div className="rounded-lg border border-subtle bg-[var(--bg-card)] p-4">
              <GlobalAgentsSettings api={api} />
            </div>
          )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
