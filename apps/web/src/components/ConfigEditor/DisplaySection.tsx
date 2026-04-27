/**
 * ConfigEditor — Display settings section.
 */

import { Monitor } from "lucide-react";
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
  return (
    <div className="border border-default rounded-lg surface-card">
      <SectionHeader
        title="Display"
        subtitle={`${data.mode} / ${data.columns} col${data.columns > 1 ? "s" : ""}${data.dashboard ? " / dashboard" : ""}`}
        icon={<Monitor className="w-3.5 h-3.5" />}
        expanded={expanded}
        onToggle={onToggle}
      />
      <CollapsibleSection expanded={expanded}>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <div>
            <FieldLabel>Layout mode</FieldLabel>
            <SelectInput
              value={data.mode}
              onChange={(v) => onChange({ mode: v as "grid" | "list" })}
              options={[
                { value: "grid", label: "Grid" },
                { value: "list", label: "List" },
              ]}
            />
          </div>
          <div>
            <FieldLabel>Columns</FieldLabel>
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
            />
            <span className="text-[13px] text-secondary">Auto-open dashboard</span>
          </div>
        </div>
      </CollapsibleSection>
    </div>
  );
}
