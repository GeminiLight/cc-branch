import { useState, useRef, useEffect, useCallback } from "react";
import { ChevronDown, Check } from "lucide-react";

interface DropdownItem {
  label: string;
  value: string;
  icon?: React.ReactNode;
  disabled?: boolean;
  description?: string;
}

interface DropdownProps {
  trigger?: React.ReactNode;
  items: DropdownItem[];
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  align?: "left" | "right";
}

export default function Dropdown({
  trigger,
  items,
  value,
  onChange,
  placeholder = "Select...",
  align = "right",
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState<number>(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const selected = items.find((i) => i.value === value);

  const firstEnabledIndex = useCallback(() => {
    return items.findIndex((item) => !item.disabled);
  }, [items]);

  const nextEnabledIndex = useCallback((start: number, direction: 1 | -1) => {
    if (items.length === 0) return -1;
    for (let step = 0; step < items.length; step += 1) {
      const index = (start + direction * step + items.length) % items.length;
      if (!items[index].disabled) return index;
    }
    return -1;
  }, [items]);

  const handle = useCallback(
    (v: string) => {
      onChange(v);
      setOpen(false);
    },
    [onChange]
  );

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node))
        setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        setOpen(false);
        return;
      }
      if (!open) return;
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setHighlighted((prev) => {
            const next = nextEnabledIndex(prev + 1, 1);
            if (next >= 0) itemRefs.current[next]?.scrollIntoView({ block: "nearest" });
            return next;
          });
          break;
        case "ArrowUp":
          e.preventDefault();
          setHighlighted((prev) => {
            const next = nextEnabledIndex(prev - 1, -1);
            if (next >= 0) itemRefs.current[next]?.scrollIntoView({ block: "nearest" });
            return next;
          });
          break;
        case "Enter":
          e.preventDefault();
          if (highlighted >= 0 && !items[highlighted].disabled) {
            handle(items[highlighted].value);
          }
          break;
        case "Home":
          e.preventDefault();
          {
            const next = firstEnabledIndex();
            setHighlighted(next);
            if (next >= 0) itemRefs.current[next]?.scrollIntoView({ block: "nearest" });
          }
          break;
        case "End":
          e.preventDefault();
          {
            const next = nextEnabledIndex(items.length - 1, -1);
            setHighlighted(next);
            if (next >= 0) itemRefs.current[next]?.scrollIntoView({ block: "nearest" });
          }
          break;
      }
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, items, highlighted, handle, firstEnabledIndex, nextEnabledIndex]);

  // Reset highlight when opening
  useEffect(() => {
    if (open) {
      const idx = items.findIndex((i) => i.value === value);
      setHighlighted(idx >= 0 && !items[idx].disabled ? idx : firstEnabledIndex());
    }
  }, [open, items, value, firstEnabledIndex]);

  // Restore focus to trigger when closing
  useEffect(() => {
    if (!open) {
      const triggerBtn = containerRef.current?.querySelector("button");
      triggerBtn?.focus();
    }
  }, [open]);

  return (
    <div ref={containerRef} className="relative inline-block">
      {trigger ? (
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="outline-none"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-activedescendant={open && highlighted >= 0 ? `dropdown-item-${items[highlighted]?.value}` : undefined}
        >
          {trigger}
        </button>
      ) : (
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="h-8 pl-3 pr-2 rounded-lg flex items-center gap-2 text-sm font-medium text-secondary hover:text-primary surface-hover border border-default transition-all"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-activedescendant={open && highlighted >= 0 ? `dropdown-item-${items[highlighted]?.value}` : undefined}
        >
          {selected?.icon && <span className="text-tertiary">{selected.icon}</span>}
          <span>{selected?.label || placeholder}</span>
          <ChevronDown
            className={`w-3.5 h-3.5 text-tertiary transition-transform duration-150 ${
              open ? "rotate-180" : ""
            }`}
          />
        </button>
      )}

      {open && (
        <div
          className={`absolute top-full mt-1.5 ${
            align === "right" ? "right-0" : "left-0"
          } z-dropdown w-44 surface-card border border-default rounded-lg py-0.5 animate-dropdown-in overflow-hidden shadow-sm`}
          role="listbox"
        >
          {items.map((item, index) => {
            const active = item.value === value;
            const isHighlighted = index === highlighted;
            return (
              <button
                type="button"
                key={item.value}
                id={`dropdown-item-${item.value}`}
                ref={(el) => { itemRefs.current[index] = el; }}
                onClick={() => {
                  if (!item.disabled) handle(item.value);
                }}
                role="option"
                aria-selected={active}
                disabled={item.disabled}
                title={item.description}
                className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 text-[13px] transition-colors text-left ${
                  item.disabled
                    ? "text-tertiary opacity-50 cursor-not-allowed"
                    : active
                    ? "text-primary surface-hover"
                    : isHighlighted
                    ? "text-primary surface-hover"
                    : "text-secondary hover:text-primary hover:surface-hover"
                }`}
              >
                {item.icon && <span className="text-tertiary">{item.icon}</span>}
                <span className="flex-1">{item.label}</span>
                {active && <Check className="w-3.5 h-3.5 text-[var(--accent)]" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
