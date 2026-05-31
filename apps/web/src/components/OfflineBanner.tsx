import { WifiOff } from "lucide-react";
import { useI18n } from "../i18n";
import { useOnlineStatus } from "../hooks/useOnlineStatus";

export default function OfflineBanner() {
  const { t } = useI18n();
  const isOnline = useOnlineStatus();

  if (isOnline) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[130] bg-[var(--warning-bg)] border-b border-[var(--warning)]/20 px-4 py-2 flex items-center justify-center gap-2">
      <WifiOff className="w-3.5 h-3.5 text-[var(--warning)]" />
      <span className="text-[12px] font-medium text-[var(--warning)]">{t("offline")}</span>
    </div>
  );
}
