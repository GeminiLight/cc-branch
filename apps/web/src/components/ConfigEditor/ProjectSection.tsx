/**
 * ConfigEditor — Project info section.
 */

import { Folder, Rocket } from "lucide-react";
import type { ReactNode } from "react";
import { useI18n } from "../../i18n";
import type { ConfigFormData } from "./types";
import { SectionHeader, CollapsibleSection, FieldLabel, SelectInput, TextInput } from "./FormPrimitives";

function SettingsGroup({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-default bg-[var(--bg-card)] overflow-hidden">
      <div className="px-3 py-2 border-b border-subtle flex items-center gap-2">
        <span className="w-7 h-7 rounded-md bg-[var(--bg-hover)] flex items-center justify-center text-tertiary shrink-0">
          {icon}
        </span>
        <h3 className="text-[12px] font-semibold text-primary">{title}</h3>
      </div>
      <div className="p-3">
        {children}
      </div>
    </div>
  );
}

export default function ProjectSection({
  data,
  onChange,
  expanded,
  onToggle,
}: {
  data: ConfigFormData;
  onChange: (patch: Partial<ConfigFormData>) => void;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { t } = useI18n();
  const defaultShell = data.defaults?.shell;
  const shellValue = typeof defaultShell === "string" ? defaultShell : defaultShell ? "custom" : "system-default";

  return (
    <section className="rounded-md transition-colors">
      <SectionHeader
        title={t("project")}
        icon={<Folder className="w-3.5 h-3.5" />}
        expanded={expanded}
        onToggle={onToggle}
      />
      <CollapsibleSection expanded={expanded}>
        <div className="space-y-3">
          <SettingsGroup title={t("projectIdentity")} icon={<Folder className="w-3.5 h-3.5" />}>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <FieldLabel required>{t("projectName")}</FieldLabel>
                <TextInput
                  value={data.project}
                  onChange={(v) => onChange({ project: v })}
                  placeholder="my-project"
                  invalid={!data.project.trim()}
                />
              </div>
              <div>
                <FieldLabel>{t("rootDirectory")}</FieldLabel>
                <TextInput
                  value={data.root}
                  onChange={(v) => onChange({ root: v })}
                  placeholder="."
                />
              </div>
            </div>
          </SettingsGroup>

          <SettingsGroup title={t("launchDefaults")} icon={<Rocket className="w-3.5 h-3.5" />}>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <FieldLabel>{t("openWithDefault")}</FieldLabel>
                <SelectInput
                  value={data.openWith || ""}
                  onChange={(value) => onChange({ openWith: value || null })}
                  options={[
                    { value: "", label: t("noneOption") },
                    { value: "cursor", label: "Cursor" },
                    { value: "vscode", label: "VS Code" },
                    { value: "warp", label: "Warp" },
                    { value: "terminal-app", label: "Terminal.app" },
                    { value: "iterm2", label: "iTerm2" },
                    { value: "auto-terminal", label: t("systemTerminal") },
                  ]}
                />
              </div>
              <div>
                <FieldLabel>{t("defaultLayoutBackend")}</FieldLabel>
                <SelectInput
                  value={data.layoutBackend || "direct"}
                  onChange={(value) => onChange({ layoutBackend: value as ConfigFormData["layoutBackend"] })}
                  options={[
                    { value: "direct", label: t("layoutBackendDirect") },
                    { value: "tmux", label: t("layoutBackendTmux") },
                  ]}
                />
              </div>
              <div>
                <FieldLabel>{t("defaultShell")}</FieldLabel>
                <SelectInput
                  value={shellValue}
                  onChange={(value) => onChange({ defaults: { shell: value === "custom" ? defaultShell ?? null : value as NonNullable<ConfigFormData["defaults"]>["shell"] } })}
                  options={[
                    { value: "system-default", label: t("shellSystemDefault") },
                    { value: "zsh", label: "zsh" },
                    { value: "bash", label: "bash" },
                    { value: "pwsh", label: "PowerShell" },
                    { value: "cmd", label: "cmd" },
                    { value: "custom", label: t("custom"), disabled: !defaultShell || typeof defaultShell === "string" },
                  ]}
                />
              </div>
            </div>
          </SettingsGroup>
        </div>
      </CollapsibleSection>
    </section>
  );
}
