import { useState, useRef, useEffect, useId, useCallback, useLayoutEffect } from "react";
import type { CSSProperties, ReactNode } from "react";
import { createPortal } from "react-dom";

interface TooltipProps {
  children: ReactNode;
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
  const [tooltipStyle, setTooltipStyle] = useState<CSSProperties>({
    position: "fixed",
    top: 0,
    left: 0,
    maxWidth: 280,
    visibility: "hidden",
    zIndex: 9999,
  });
  const wrapperRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const id = useId();
  const tooltipId = `tooltip-${id}`;

  const updatePosition = useCallback(() => {
    const trigger = wrapperRef.current;
    if (!trigger) return;

    const rect = trigger.getBoundingClientRect();
    const viewportWidth = Math.max(window.innerWidth, 320);
    const viewportHeight = Math.max(window.innerHeight, 240);
    const gap = 8;
    const maxWidth = Math.min(280, viewportWidth - 16);
    const estimatedWidth = Math.min(maxWidth, Math.max(96, content.length * 6 + 24));
    const tooltipWidth = Math.min(maxWidth, tooltipRef.current?.offsetWidth || estimatedWidth);
    const tooltipHeight = tooltipRef.current?.offsetHeight || 28;

    let top = rect.bottom + gap;
    let left = rect.left + rect.width / 2 - tooltipWidth / 2;

    if (side === "top") {
      top = rect.top - gap - tooltipHeight;
      left = rect.left + rect.width / 2 - tooltipWidth / 2;
    } else if (side === "left") {
      top = rect.top + rect.height / 2 - tooltipHeight / 2;
      left = rect.left - gap - tooltipWidth;
    } else if (side === "right") {
      top = rect.top + rect.height / 2 - tooltipHeight / 2;
      left = rect.right + gap;
    }

    if (left < 8) left = 8;
    if (left + tooltipWidth > viewportWidth - 8) left = viewportWidth - tooltipWidth - 8;
    if (top < 8) top = 8;
    if (top + tooltipHeight > viewportHeight - 8) top = viewportHeight - tooltipHeight - 8;

    setTooltipStyle({
      position: "fixed",
      top,
      left,
      maxWidth,
      visibility: "visible",
      zIndex: 9999,
    });
  }, [content, side]);

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

  useLayoutEffect(() => {
    if (mounted) updatePosition();
  }, [mounted, updatePosition]);

  useEffect(() => {
    if (!mounted) return;
    const onScroll = () => updatePosition();
    const onResize = () => updatePosition();
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onResize);
    };
  }, [mounted, updatePosition]);

  const tooltipContent = mounted ? (
    <div
      id={tooltipId}
      ref={tooltipRef}
      role="tooltip"
      className="z-tooltip pointer-events-none"
      style={{
        ...tooltipStyle,
        opacity: visible ? 1 : 0,
        transition: "opacity 120ms ease",
      }}
    >
      <div className="px-2 py-1 rounded surface-card border border-default shadow-sm">
        <span className="text-[11px] font-medium text-primary break-words">
          {content}
        </span>
      </div>
    </div>
  ) : null;

  return (
    <div
      ref={wrapperRef}
      className="inline-flex"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      aria-describedby={mounted ? tooltipId : undefined}
    >
      {children}
      {tooltipContent && createPortal(tooltipContent, document.body)}
    </div>
  );
}
