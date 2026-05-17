import { useI18n } from "../i18n";

export default function SkipLink() {
  const { t } = useI18n();
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-toast focus:h-8 focus:px-3 focus:rounded focus:bg-[var(--accent)] focus:text-white focus:text-[13px] focus:font-medium focus:flex focus:items-center"
    >
      {t("skipToContent")}
    </a>
  );
}
