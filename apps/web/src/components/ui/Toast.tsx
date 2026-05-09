import { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, XCircle, Info, X } from "lucide-react";
import { useI18n } from "../../i18n";

interface ToastItem {
  id: string;
  message: string;
  type: "success" | "error" | "info";
  duration: number;
}

interface ToastCtx {
  success: (m: string, d?: number) => void;
  error: (m: string, d?: number) => void;
  info: (m: string, d?: number) => void;
}

const ToastContext = createContext<ToastCtx>({
  success: () => {},
  error: () => {},
  info: () => {},
});

const MAX_TOASTS = 5;

export function useToast() {
  return useContext(ToastContext);
}

function ToastBar({ toast, onRemove }: { toast: ToastItem; onRemove: (id: string) => void }) {
  const { t } = useI18n();
  const config = {
    success: {
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-[var(--success)]" />,
      bar: "bg-[var(--success)]",
    },
    error: {
      icon: <XCircle className="w-3.5 h-3.5 text-[var(--danger)]" />,
      bar: "bg-[var(--danger)]",
    },
    info: {
      icon: <Info className="w-3.5 h-3.5 text-[var(--accent)]" />,
      bar: "bg-[var(--accent)]",
    },
  }[toast.type];

  const isAssertive = toast.type === "error";

  return (
    <div
      className="animate-toast-in group relative w-full max-w-sm surface-card border border-default rounded-lg overflow-hidden"
      role={isAssertive ? "alert" : "status"}
      aria-live={isAssertive ? "assertive" : "polite"}
    >
      <div className="flex items-center gap-2.5 px-3.5 py-2.5">
        {config.icon}
        <p className="text-[13px] text-primary flex-1">{toast.message}</p>
        <button
          type="button"
          onClick={() => onRemove(toast.id)}
          className="w-8 h-8 rounded-md flex items-center justify-center text-tertiary hover:text-primary hover:surface-hover transition-colors"
          aria-label={t("dismissNotification")}
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="h-[2px] bg-[var(--border-subtle)] overflow-hidden">
        <div
          className={`h-full ${config.bar} toast-progress-bar`}
          style={{
            width: "100%",
            animation: `toast-progress ${toast.duration}ms linear forwards`,
          }}
          onAnimationEnd={() => onRemove(toast.id)}
        />
      </div>
    </div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const remove = useCallback((id: string) => {
    setToasts((p) => p.filter((t) => t.id !== id));
  }, []);
  const add = useCallback(
    (type: ToastItem["type"], message: string, duration = 3000) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 5)}`;
      setToasts((p) => {
        const next = [...p, { id, message, type, duration }];
        if (next.length > MAX_TOASTS) return next.slice(next.length - MAX_TOASTS);
        return next;
      });
    },
    []
  );

  return (
    <ToastContext.Provider
      value={{
        success: useCallback((m, d?) => add("success", m, d), [add]),
        error: useCallback((m, d?) => add("error", m, d), [add]),
        info: useCallback((m, d?) => add("info", m, d), [add]),
      }}
    >
      {children}
      <div className="fixed bottom-4 right-4 z-toast flex flex-col items-end gap-2 pointer-events-none">
        {toasts.map((t, i) => (
          <div
            key={t.id}
            className="pointer-events-auto"
            style={{
              transform: `scale(${1 - (toasts.length - 1 - i) * 0.05})`,
              opacity: 1 - (toasts.length - 1 - i) * 0.2,
            }}
          >
            <ToastBar toast={t} onRemove={remove} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
