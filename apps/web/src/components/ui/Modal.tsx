import { useEffect, useRef, useCallback, useId } from "react";
import { X } from "lucide-react";
import { useI18n } from "../../i18n";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  icon?: React.ReactNode;
  children?: React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  onConfirm?: () => void;
  variant?: "default" | "danger";
}

export default function Modal({
  isOpen,
  onClose,
  title,
  description,
  icon,
  children,
  confirmText,
  cancelText,
  onConfirm,
  variant = "default",
}: ModalProps) {
  const { t } = useI18n();
  const overlayRef = useRef<HTMLDivElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  // Focus trap
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab" || !modalRef.current) return;

      const focusable = modalRef.current.querySelectorAll<HTMLElement>(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (!isOpen) return;

    // Save previous focus
    previousFocus.current = document.activeElement as HTMLElement;

    // Lock body scroll
    const scrollBarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = "hidden";
    if (scrollBarWidth > 0) {
      document.body.style.paddingRight = `${scrollBarWidth}px`;
    }

    document.addEventListener("keydown", handleKeyDown);

    // Auto-focus first element
    const timer = setTimeout(() => {
      const focusable = modalRef.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
      );
      focusable?.[0]?.focus();
    }, 50);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
      document.body.style.paddingRight = "";
      clearTimeout(timer);
      // Restore focus
      previousFocus.current?.focus();
    };
  }, [isOpen, handleKeyDown]);

  const baseId = useId();

  if (!isOpen) return null;

  const confirmClass =
    variant === "danger"
      ? "bg-[var(--danger)] text-white hover:opacity-90"
      : "bg-[var(--accent)] text-white hover:opacity-90";
  const titleId = `modal-title-${baseId}`;
  const descId = description ? `modal-desc-${baseId}` : undefined;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-modal flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={descId}
    >
      <button
        type="button"
        className="absolute inset-0 w-full h-full bg-black/20 backdrop-blur-sm animate-fade-in cursor-default"
        onClick={onClose}
        aria-hidden="true"
        tabIndex={-1}
      />
      <div
        ref={modalRef}
        className="relative z-10 w-full max-w-sm surface-card border border-default rounded-lg animate-modal-in"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 w-8 h-8 rounded flex items-center justify-center text-tertiary hover:text-primary hover:surface-hover transition-colors z-10"
          aria-label={t("cancel")}
        >
          <X className="w-4 h-4" />
        </button>

        <div className="p-5 pb-4">
          {icon && (
            <div
              className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${
                variant === "danger" ? "danger-bg" : "bg-[var(--accent-bg)]"
              }`}
            >
              {icon}
            </div>
          )}
          <h3 id={titleId} className="text-[15px] font-semibold text-primary pr-5">
            {title}
          </h3>
          {description && (
            <p id={descId} className="text-[13px] text-secondary mt-1.5 leading-relaxed">
              {description}
            </p>
          )}
          {children && <div className="mt-3">{children}</div>}
        </div>

        <div className="px-5 py-4 border-t border-default flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="h-8 px-3 rounded text-[13px] font-medium text-secondary hover:text-primary surface-hover transition-colors"
          >
            {cancelText || t("cancel")}
          </button>
          {onConfirm && (
            <button
              type="button"
              onClick={onConfirm}
              className={`h-8 px-3 rounded text-[13px] font-medium transition-opacity ${confirmClass}`}
            >
              {confirmText || t("confirm")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
