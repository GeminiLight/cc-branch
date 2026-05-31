/**
 * EmptyState — unified empty state component.
 *
 * Usage: loading | error | empty | custom icon
 */

import type { ReactNode } from "react";
import { Activity, AlertTriangle, Loader2 } from "lucide-react";

interface EmptyStateProps {
  variant?: "empty" | "error" | "loading";
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

const variantConfig = {
  empty: {
    iconBg: "bg-[var(--accent-bg)] border-[var(--accent-border)]",
    iconColor: "text-[var(--accent)]",
    defaultIcon: <Activity className="w-6 h-6" />,
  },
  error: {
    iconBg: "danger-bg border-[var(--danger)]/10",
    iconColor: "danger",
    defaultIcon: <AlertTriangle className="w-6 h-6" />,
  },
  loading: {
    iconBg: "bg-[var(--border-subtle)]",
    iconColor: "text-tertiary",
    defaultIcon: <Loader2 className="w-6 h-6 animate-spin" />,
  },
};

export default function EmptyState({
  variant = "empty",
  icon,
  title,
  description,
  action,
  className = "",
}: EmptyStateProps) {
  const cfg = variantConfig[variant];

  return (
    <div className={`text-center py-20 max-w-sm mx-auto ${className}`}>
      <div
        className={`w-12 h-12 rounded-xl border flex items-center justify-center mx-auto mb-4 ${cfg.iconBg}`}
      >
        <span className={cfg.iconColor}>{icon || cfg.defaultIcon}</span>
      </div>
      <h3 className="text-[15px] font-semibold text-primary mb-1.5">{title}</h3>
      {description && (
        <p className="text-[13px] text-secondary mb-5">{description}</p>
      )}
      {action && <div className="flex justify-center">{action}</div>}
    </div>
  );
}
