import type { TabLayout } from "./workspace-model";

function LayoutGlyph({ layout }: { layout: TabLayout }) {
  const base = "rounded-[2px] border border-current bg-current/15";
  if (layout === "vertical") {
    return (
      <span className="grid h-4 w-5 grid-rows-2 gap-0.5" aria-hidden="true">
        <span className={base} />
        <span className={base} />
      </span>
    );
  }
  if (layout === "main-left") {
    return (
      <span className="grid h-4 w-5 grid-cols-[1.25fr_0.75fr] grid-rows-2 gap-0.5" aria-hidden="true">
        <span className={`${base} row-span-2`} />
        <span className={base} />
        <span className={base} />
      </span>
    );
  }
  if (layout === "main-top") {
    return (
      <span className="grid h-4 w-5 grid-cols-2 grid-rows-[1.2fr_0.8fr] gap-0.5" aria-hidden="true">
        <span className={`${base} col-span-2`} />
        <span className={base} />
        <span className={base} />
      </span>
    );
  }
  if (layout === "grid") {
    return (
      <span className="grid h-4 w-5 grid-cols-2 grid-rows-2 gap-0.5" aria-hidden="true">
        <span className={base} />
        <span className={base} />
        <span className={base} />
        <span className={base} />
      </span>
    );
  }
  if (layout === "auto") {
    return (
      <span className="grid h-4 w-5 grid-cols-[1fr_0.7fr] grid-rows-2 gap-0.5" aria-hidden="true">
        <span className={`${base} row-span-2`} />
        <span className={base} />
        <span className={base} />
      </span>
    );
  }
  return (
    <span className="grid h-4 w-5 grid-cols-2 gap-0.5" aria-hidden="true">
      <span className={base} />
      <span className={base} />
    </span>
  );
}

export default function LayoutPicker({
  value,
  options,
  onChange,
  compact = false,
}: {
  value: TabLayout;
  options: Array<{ value: string; label: string }>;
  onChange: (value: TabLayout) => void;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex flex-wrap items-center gap-1 rounded-md border border-default bg-[var(--bg-hover)] p-1 ${
        compact ? "max-w-[230px]" : ""
      }`}
    >
      {options.map((option) => {
        const selected = option.value === value;
        const optionValue = option.value as TabLayout;
        return (
          <button
            type="button"
            key={option.value}
            onClick={() => onChange(optionValue)}
            className={`control-touch rounded text-[11px] font-semibold transition-colors ${
              compact ? "min-h-7 min-w-8 px-1.5" : "min-h-8 px-2"
            } ${
              selected
                ? "bg-[var(--bg-card)] text-[var(--accent)] shadow-sm"
                : "text-tertiary hover:text-primary hover:bg-[var(--bg-card)]/70"
            }`}
            aria-pressed={selected}
            aria-label={option.label}
            title={option.label}
          >
            {compact ? (
              <>
                <LayoutGlyph layout={optionValue} />
                <span className="sr-only">{option.label}</span>
              </>
            ) : (
              <span className="inline-flex items-center gap-1.5">
                <LayoutGlyph layout={optionValue} />
                {option.label}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
