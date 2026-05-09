import { Check, Globe, MonitorCog, Moon, Sun } from "lucide-react";
import { useI18n, type Lang } from "../i18n";
import { useTheme, type Theme } from "../theme/ThemeProvider";
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

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { t, lang, setLang } = useI18n();
  const { theme, setTheme } = useTheme();

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t("settings")}
      description={t("settingsDesc")}
      icon={<MonitorCog className="w-5 h-5 text-[var(--accent)]" />}
    >
      <div className="space-y-4">
        <section>
          <div className="flex items-center gap-2 mb-2">
            <Sun className="w-3.5 h-3.5 text-tertiary" />
            <h4 className="text-[12px] font-semibold text-primary">{t("themeSwitch")}</h4>
          </div>
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
        </section>

        <section>
          <div className="flex items-center gap-2 mb-2">
            <Globe className="w-3.5 h-3.5 text-tertiary" />
            <h4 className="text-[12px] font-semibold text-primary">{t("langSwitch")}</h4>
          </div>
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
        </section>
      </div>
    </Modal>
  );
}
