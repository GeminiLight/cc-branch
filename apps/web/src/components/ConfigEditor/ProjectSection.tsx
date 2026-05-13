/**
 * ConfigEditor — Project info section.
 */

import { ChevronDown, Folder } from "lucide-react";
import { useI18n } from "../../i18n";
import type { ConfigFormData } from "./types";
import { SectionHeader, CollapsibleSection, FieldLabel, SelectInput, TextInput } from "./FormPrimitives";

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
        subtitle={`${data.project} / ${data.root}`}
        icon={<Folder className="w-3.5 h-3.5" />}
        expanded={expanded}
        onToggle={onToggle}
      />
      <CollapsibleSection expanded={expanded}>
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
          <details className="group sm:col-span-2 rounded-md border border-default bg-[var(--bg-card)]">
            <summary className="flex items-center justify-between gap-3 px-3 py-2 cursor-pointer text-[12px] font-semibold text-secondary hover:text-primary">
              <span>{t("advancedDefaults")}</span>
              <ChevronDown className="w-3.5 h-3.5 text-tertiary transition-transform group-open:rotate-180" />
            </summary>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 border-t border-subtle px-3 pb-3 pt-3">
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
                    { value: "iterm", label: "iTerm" },
                    { value: "terminal", label: "Terminal" },
                    { value: "auto-terminal", label: "Auto terminal" },
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
          </details>
        </div>
      </CollapsibleSection>
    </section>
  );
}
