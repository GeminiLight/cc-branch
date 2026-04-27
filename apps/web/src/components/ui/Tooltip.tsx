import { useState, useRef, useEffect, useId } from "react";

interface TooltipProps {
  children: React.ReactNode;
  content: string;
  side?: "top" | "bottom" | "left" | "right";
  delay?: number;
}

export default function Tooltip({
  children,
  content,
  side = "bottom",
  delay = 350,
}: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const [mounted, setMounted] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const id = useId();
  const tooltipId = `tooltip-${id}`;

  const show = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setMounted(true);
      requestAnimationFrame(() => setVisible(true));
    }, delay);
  };
  const hide = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setVisible(false);
    timerRef.current = setTimeout(() => setMounted(false), 120);
  };

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  const sideClass = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-1.5",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-1.5",
    left: "right-full top-1/2 -translate-y-1/2 mr-1.5",
    right: "left-full top-1/2 -translate-y-1/2 ml-1.5",
  }[side];

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      aria-describedby={mounted ? tooltipId : undefined}
    >
      {children}
      {mounted && (
        <div
          id={tooltipId}
          role="tooltip"
          className={`absolute z-tooltip pointer-events-none ${sideClass}`}
          style={{ opacity: visible ? 1 : 0, transition: "opacity 120ms ease" }}
        >
          <div className="px-2 py-1 rounded surface-card border border-default shadow-sm max-w-xs">
            <span className="text-[11px] font-medium text-primary break-words">
              {content}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
