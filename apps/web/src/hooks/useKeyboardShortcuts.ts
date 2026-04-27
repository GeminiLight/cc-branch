import { useEffect, useRef } from "react";

interface ShortcutHandlers {
  onTab1?: () => void;
  onTab2?: () => void;
  onTab3?: () => void;
  onSave?: () => void;
  onEscape?: () => void;
}

export function useKeyboardShortcuts(handlers: ShortcutHandlers) {
  const handlersRef = useRef(handlers);
  // Keep ref up-to-date without triggering effect re-runs
  handlersRef.current = handlers;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const h = handlersRef.current;
      // Only trigger when not in an input/textarea
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        // Allow Cmd+S and Escape even in inputs
        if (e.key === "Escape") {
          h.onEscape?.();
          return;
        }
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
          e.preventDefault();
          h.onSave?.();
          return;
        }
        return;
      }

      // Tab switching: Ctrl/Cmd + number
      if ((e.metaKey || e.ctrlKey) && !e.altKey) {
        if (e.key === "1") {
          e.preventDefault();
          h.onTab1?.();
          return;
        }
        if (e.key === "2") {
          e.preventDefault();
          h.onTab2?.();
          return;
        }
        if (e.key === "3") {
          e.preventDefault();
          h.onTab3?.();
          return;
        }
      }

      // Save shortcut
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        h.onSave?.();
        return;
      }

      if (e.key === "Escape") {
        h.onEscape?.();
        return;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);
}
