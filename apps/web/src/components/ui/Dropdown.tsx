import { useState, useRef, useEffect, useCallback, useLayoutEffect, useId } from "react";
import type { CSSProperties } from "react";
import { createPortal } from "react-dom";
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
  ariaLabel?: string;
}

export default function Dropdown({
  trigger,
  items,
  value,
  onChange,
  placeholder = "Select...",
  align = "right",
  ariaLabel,
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState<number>(-1);
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({});
  const containerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const wasOpenRef = useRef(false);
  const shouldRestoreFocusRef = useRef(false);
  const selected = items.find((i) => i.value === value);
  const menuId = useId();
  const getOptionId = useCallback((index: number) => `${menuId}-item-${index}`, [menuId]);

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
      shouldRestoreFocusRef.current = true;
      setOpen(false);
    },
    [onChange]
  );

  // Compute menu position based on trigger
  const updatePosition = useCallback(() => {
    const triggerEl = containerRef.current;
    if (!triggerEl) return;
    const rect = triggerEl.getBoundingClientRect();
    const viewportWidth = Math.max(window.innerWidth, 320);
    const maxMenuWidth = viewportWidth - 16;
    const longestLabelLength = items.reduce((max, item) => Math.max(max, item.label.length), 0);
    const estimatedLabelWidth = longestLabelLength * 8 + 56;
    const menuWidth = Math.min(
      Math.max(176, Math.ceil(rect.width), estimatedLabelWidth),
      maxMenuWidth
    );
    const gap = 6; // mt-1.5
    const itemHeight = 40; // approx per item
    const menuHeight = Math.min(items.length * itemHeight + 8, window.innerHeight - 32);

    let left: number;
    if (align === "right") {
      left = rect.right - menuWidth;
    } else {
      left = rect.left;
    }

    // Horizontal bounds
    if (left < 8) left = 8;
    if (left + menuWidth > window.innerWidth - 8) {
      left = window.innerWidth - menuWidth - 8;
    }

    // Vertical bounds: flip upward if would overflow bottom
    let top = rect.bottom + gap;
    if (top + menuHeight > window.innerHeight - 8) {
      top = rect.top - gap - menuHeight;
    }
    // If flipping would put it above viewport, clamp to top
    if (top < 8) top = 8;

    setMenuStyle({
      position: "fixed",
      top,
      left,
      width: menuWidth,
      maxHeight: menuHeight,
      overflowY: "auto",
      zIndex: 9999,
    });
  }, [align, items]);

  useLayoutEffect(() => {
    if (open) {
      updatePosition();
    }
  }, [open, updatePosition]);

  useEffect(() => {
    if (!open) return;
    const onScroll = () => updatePosition();
    const onResize = () => updatePosition();
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onResize);
    };
  }, [open, updatePosition]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        const target = e.target as Node;
        if (menuRef.current?.contains(target)) return;
        shouldRestoreFocusRef.current = false;
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        shouldRestoreFocusRef.current = true;
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
    if (wasOpenRef.current && !open && shouldRestoreFocusRef.current) {
      const triggerBtn = containerRef.current?.querySelector("button");
      triggerBtn?.focus();
    }
    wasOpenRef.current = open;
    if (!open) shouldRestoreFocusRef.current = false;
  }, [open]);

  const menuContent = open ? (
    <div
      id={menuId}
      ref={menuRef}
      style={menuStyle}
      className="surface-card border border-default rounded-lg py-0.5 px-1 animate-dropdown-in shadow-lg"
      role="listbox"
    >
      {items.map((item, index) => {
        const active = item.value === value;
        const isHighlighted = index === highlighted;
        return (
          <button
            type="button"
            key={item.value}
            id={getOptionId(index)}
            ref={(el) => { itemRefs.current[index] = el; }}
            onClick={() => {
              if (!item.disabled) handle(item.value);
            }}
            role="option"
            aria-selected={active}
            disabled={item.disabled}
            title={item.description}
            className={`w-full flex items-center gap-2.5 px-2.5 py-2 text-[13px] transition-colors text-left rounded-md my-0.5 ${
              item.disabled
                ? "text-tertiary opacity-50 cursor-not-allowed"
                : active
                ? "text-primary bg-[var(--accent-bg)]"
                : isHighlighted
                ? "text-primary surface-hover"
                : "text-secondary hover:text-primary hover:surface-hover"
            }`}
          >
            {item.icon && <span className="text-tertiary">{item.icon}</span>}
            <span className="flex-1 min-w-0 truncate">{item.label}</span>
            {active && <Check className="w-3.5 h-3.5 text-[var(--accent)] shrink-0" />}
          </button>
        );
      })}
    </div>
  ) : null;

  return (
    <>
      <div ref={containerRef} className="relative inline-block">
        {trigger ? (
          <button
            type="button"
            onClick={() => {
              shouldRestoreFocusRef.current = false;
              setOpen((o) => !o);
            }}
            className="outline-none"
            aria-label={ariaLabel}
            aria-haspopup="listbox"
            aria-expanded={open}
            aria-controls={open ? menuId : undefined}
            aria-activedescendant={open && highlighted >= 0 ? getOptionId(highlighted) : undefined}
          >
            {trigger}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => {
              shouldRestoreFocusRef.current = false;
              setOpen((o) => !o);
            }}
            className="h-8 pl-3 pr-2 rounded-lg flex items-center gap-2 text-sm font-medium text-secondary hover:text-primary surface-hover border border-default transition-all"
            aria-label={ariaLabel}
            aria-haspopup="listbox"
            aria-expanded={open}
            aria-controls={open ? menuId : undefined}
            aria-activedescendant={open && highlighted >= 0 ? getOptionId(highlighted) : undefined}
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
      </div>
      {menuContent && createPortal(menuContent, document.body)}
    </>
  );
}
