/**
 * ConfigEditor — Project info section.
 */

import { Folder } from "lucide-react";
import { useI18n } from "../../i18n";
import type { ConfigFormData } from "./types";
import { SectionHeader, CollapsibleSection, FieldLabel, TextInput } from "./FormPrimitives";

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
        </div>
      </CollapsibleSection>
    </section>
  );
}
