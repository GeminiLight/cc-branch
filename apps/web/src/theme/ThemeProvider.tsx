/**
 * Theme provider (light / dark).
 *
 * Uses Tailwind's `dark` class strategy. Toggles `.dark` on <html>
 * and persists preference to localStorage.
 */

import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { getLocalStorageItem, setLocalStorageItem } from "../utils/browserStorage";

export type Theme = "light" | "dark";

const STORAGE_KEY = "cc-branch-theme";

interface ThemeCtx {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeCtx>({
  theme: "light",
  setTheme: () => {},
  toggle: () => {},
});

function getInitialTheme(): Theme {
  const stored = readStoredTheme();
  if (stored === "light" || stored === "dark") return stored;
  return systemPrefersDark() ? "dark" : "light";
}

function readStoredTheme(): Theme | null {
  const stored = getLocalStorageItem(STORAGE_KEY) as Theme | null;
  return stored === "light" || stored === "dark" ? stored : null;
}

function persistTheme(theme: Theme) {
  setLocalStorageItem(STORAGE_KEY, theme);
}

function systemPrefersDark(): boolean {
  try {
    return Boolean(window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  } catch {
    return false;
  }
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Listen for system theme changes
  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mq) return;
    const handler = (e: MediaQueryListEvent | MediaQueryList) => {
      // Only auto-switch if user hasn't explicitly set a preference
      if (!readStoredTheme()) {
        setThemeState(e.matches ? "dark" : "light");
      }
    };
    if (typeof mq.addEventListener === "function") {
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
    if (typeof mq.addListener === "function") {
      mq.addListener(handler);
      return () => mq.removeListener?.(handler);
    }
  }, []);

  const setTheme = useCallback((t: Theme) => {
    persistTheme(t);
    setThemeState(t);
  }, []);

  const toggle = useCallback(() => {
    setThemeState((prev) => {
      const next = prev === "light" ? "dark" : "light";
      persistTheme(next);
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
