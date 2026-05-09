/**
 * ConfigEditor — Display settings section.
 */

import { Monitor } from "lucide-react";
import { useI18n } from "../../i18n";
import type { DisplayConfig } from "./types";
import {
  SectionHeader,
  CollapsibleSection,
  FieldLabel,
  SelectInput,
  NumberInput,
  Toggle,
} from "./FormPrimitives";

export default function DisplaySection({
  data,
  onChange,
  expanded,
  onToggle,
}: {
  data: DisplayConfig;
  onChange: (patch: Partial<DisplayConfig>) => void;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { t } = useI18n();
  const modeLabel = data.mode === "grid" ? t("grid") : t("list");

  return (
    <section className="rounded-md transition-colors">
      <SectionHeader
        title={t("display")}
        subtitle={`${modeLabel} / ${data.columns} ${t("columns")}${data.dashboard ? ` / ${t("dashboard")}` : ""}`}
        icon={<Monitor className="w-3.5 h-3.5" />}
        expanded={expanded}
        onToggle={onToggle}
      />
      <CollapsibleSection expanded={expanded}>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <div>
            <FieldLabel>{t("layoutMode")}</FieldLabel>
            <SelectInput
              value={data.mode}
              onChange={(v) => onChange({ mode: v as "grid" | "list" })}
              options={[
                { value: "grid", label: t("grid") },
                { value: "list", label: t("list") },
              ]}
            />
          </div>
          <div>
            <FieldLabel>{t("columns")}</FieldLabel>
            <NumberInput
              value={data.columns}
              onChange={(v) => onChange({ columns: Math.max(1, Math.min(6, v)) })}
              min={1}
              max={6}
            />
          </div>
          <div className="flex items-center gap-2.5 pb-1">
            <Toggle
              checked={data.dashboard}
              onChange={(v) => onChange({ dashboard: v })}
              label={t("autoOpenDashboard")}
            />
            <span className="text-[13px] text-secondary">{t("autoOpenDashboard")}</span>
          </div>
        </div>
      </CollapsibleSection>
    </section>
  );
}
