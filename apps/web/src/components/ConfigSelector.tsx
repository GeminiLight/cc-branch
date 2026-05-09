import { FileCode2 } from "lucide-react";
import type { ConfigOption } from "../types";
import { useI18n } from "../i18n";
import Dropdown from "./ui/Dropdown";

interface ConfigSelectorProps {
  configs: ConfigOption[];
  selectedPath?: string;
  onSelect: (path: string) => void;
}

export default function ConfigSelector({ configs, selectedPath, onSelect }: ConfigSelectorProps) {
  const { t } = useI18n();
  const selected = configs.find((item) => item.path === selectedPath) || configs[0];

  if (configs.length <= 1) {
    return (
      <div className="hidden sm:flex control-touch items-center gap-1.5 rounded-md border border-default bg-[var(--bg-card)]/70 px-2.5 text-[12px] font-medium text-tertiary">
        <FileCode2 className="w-3.5 h-3.5" />
        <span className="max-w-32 truncate">{selected?.label || t("defaultConfig")}</span>
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
        description: config.path,
        icon: <FileCode2 className="w-3.5 h-3.5" />,
      }))}
      trigger={
        <div className="control-touch px-2.5 rounded-md flex items-center gap-1.5 text-[12px] font-medium text-secondary hover:text-primary hover:surface-hover transition-colors cursor-pointer">
          <FileCode2 className="w-3.5 h-3.5" />
          <span className="hidden sm:inline max-w-32 truncate">{selected?.label || t("defaultConfig")}</span>
        </div>
      }
    />
  );
}
