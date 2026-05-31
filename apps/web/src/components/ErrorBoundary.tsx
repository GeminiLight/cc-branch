import { Component, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { useI18n } from "../i18n";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundaryInner extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    if (import.meta.env.DEV) {
      console.error("ErrorBoundary caught:", error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return <ErrorFallback error={this.state.error} onReset={() => this.setState({ hasError: false })} />;
    }
    return this.props.children;
  }
}

function ErrorFallback({ error, onReset }: { error?: Error; onReset: () => void }) {
  const { t } = useI18n();
  return (
    <div className="min-h-[100dvh] surface-page flex items-center justify-center p-4">
      <div className="max-w-sm w-full text-center">
        <div className="w-12 h-12 rounded-xl danger-bg flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-6 h-6 danger" />
        </div>
        <h2 className="text-base font-semibold text-primary mb-2">{t("errorLoading")}</h2>
        <p className="text-[13px] text-secondary mb-6">
          {error?.message || t("unknownError")}
        </p>
        <button
          type="button"
          onClick={() => {
            onReset();
            window.location.reload();
          }}
          className="inline-flex items-center gap-2 h-9 px-4 rounded-md text-[13px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          {t("refresh")}
        </button>
      </div>
    </div>
  );
}

export default ErrorBoundaryInner;
