import { ChevronDown, FileCode2 } from "lucide-react";
import type { ConfigOption } from "../types";
import { useI18n } from "../i18n";
import Dropdown from "./ui/Dropdown";

interface ConfigSelectorProps {
  configs: ConfigOption[];
  selectedPath?: string;
  onSelect: (path: string) => void;
}

function selectedConfig(configs: ConfigOption[], selectedPath?: string): ConfigOption | undefined {
  return configs.find((item) => item.path === selectedPath) || configs.find((item) => item.selected) || configs[0];
}

function configCountText(t: (key: string, vars?: Record<string, string | number>) => string, count: number): string {
  return t(count === 1 ? "configCountOne" : "configCount", { count });
}

export function ConfigContextNotice({ configs, selectedPath }: Omit<ConfigSelectorProps, "onSelect">) {
  const { t } = useI18n();
  const selected = selectedConfig(configs, selectedPath);

  if (!selected) return null;

  return (
    <div className="page-shell">
      <div className="min-h-10 rounded-md border border-default surface-card px-3 py-2 flex flex-col lg:flex-row lg:items-center gap-2 lg:gap-3 text-[12px]">
        <div className="flex items-center gap-2 min-w-0">
          <FileCode2 className="w-3.5 h-3.5 shrink-0 text-tertiary" />
          <span className="text-tertiary font-medium">{t("activeConfig")}</span>
          <span className="rounded-md bg-[var(--accent-bg)] px-1.5 py-0.5 text-[11px] font-semibold text-[var(--accent)]">
            {selected.label}
          </span>
          <span className="text-tertiary">{configCountText(t, configs.length)}</span>
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2 min-w-0 text-[11px] font-mono text-tertiary">
          <span className="truncate" title={selected.path}>{selected.path}</span>
          <span className="hidden sm:inline text-muted">·</span>
          <span className="text-muted">{t("stateFile")}:</span>
          <span className="truncate" title={selected.state_path}>
            {selected.state_path}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function ConfigSelector({ configs, selectedPath, onSelect }: ConfigSelectorProps) {
  const { t } = useI18n();
  const selected = selectedConfig(configs, selectedPath);
  const countLabel = configCountText(t, configs.length);

  if (configs.length <= 1) {
    return (
      <div
        className="control-touch items-center gap-2 rounded-md border border-default bg-[var(--bg-card)]/70 px-2.5 text-[12px] font-medium text-tertiary flex"
        title={selected?.path}
      >
        <FileCode2 className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">{t("config")}</span>
        <span className="max-w-28 truncate text-secondary">{selected?.label || t("defaultConfig")}</span>
      </div>
    );
  }

  return (
    <Dropdown
      align="right"
      value={selected?.path}
      onChange={onSelect}
      ariaLabel={t("workspaceConfig")}
      items={configs.map((config) => ({
        label: config.label,
        value: config.path,
        disabled: !config.exists,
        description: `${config.is_default ? `${t("defaultConfig")} · ` : ""}${config.path}`,
        icon: <FileCode2 className="w-3.5 h-3.5" />,
      }))}
      trigger={
        <div
          className="control-touch px-2.5 rounded-md flex items-center gap-2 text-[12px] font-medium text-secondary hover:text-primary hover:surface-hover transition-colors cursor-pointer"
          title={selected?.path}
        >
          <FileCode2 className="w-3.5 h-3.5" />
          <span className="hidden md:inline text-tertiary">{t("config")}</span>
          <span className="max-w-28 truncate">{selected?.label || t("defaultConfig")}</span>
          <span className="hidden sm:inline rounded-md bg-[var(--bg-hover)] px-1.5 py-0.5 text-[10px] font-semibold text-tertiary">
            {countLabel}
          </span>
          <ChevronDown className="w-3 h-3 text-tertiary" />
        </div>
      }
    />
  );
}
