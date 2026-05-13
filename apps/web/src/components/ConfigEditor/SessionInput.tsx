import { useEffect, useState } from "react";
import { ChevronsUpDown, Clock3 } from "lucide-react";
import { useI18n } from "../../i18n";
import { useAgentSessions } from "../../hooks";
import type { AgentSessionInfo, WorkspaceScope } from "../../types";
import Dropdown from "../ui/Dropdown";
import { displayAgentName, normalizeAgentKey } from "../ui/AgentMark";

function sessionDescription(session: AgentSessionInfo): string {
  const shortId = session.id.length > 12 ? `${session.id.slice(0, 8)}...${session.id.slice(-4)}` : session.id;
  if (!session.updated_at) return shortId;
  const date = new Date(session.updated_at);
  if (Number.isNaN(date.getTime())) return shortId;
  return `${shortId} · ${date.toLocaleDateString()}`;
}

function sessionIntent(value: string): "auto" | "fresh" | "resume" {
  if (!value || value === "auto") return "auto";
  if (value === "fresh") return "fresh";
  return "resume";
}

export default function SessionInput({
  value,
  onChange,
  agent,
  scope,
}: {
  value: string;
  onChange: (value: string) => void;
  agent?: string | null;
  scope?: WorkspaceScope;
}) {
  const { t } = useI18n();
  const agentKey = normalizeAgentKey(agent);
  const [forcedIntent, setForcedIntent] = useState<"resume" | null>(null);
  const inferredIntent = sessionIntent(value);
  const intent = forcedIntent ?? inferredIntent;
  const { data, isFetching: loading } = useAgentSessions(scope, Boolean(agentKey) && intent === "resume", agentKey);
  const sessions = data?.sessions || [];
  const matchingSessions = agentKey
    ? sessions.filter((session) => normalizeAgentKey(session.agent) === agentKey)
    : [];
  const displayAgent = displayAgentName(agent);
  const items = matchingSessions.length > 0
    ? matchingSessions.map((session) => ({
        value: session.id,
        label: session.label || session.id,
        description: sessionDescription(session),
        icon: <Clock3 className="w-3.5 h-3.5" />,
      }))
    : [{
        value: "__empty",
        label: loading ? t("loadingSessions") : t("noSessionsFound"),
        description: agent ? t("manualSessionAllowed") : t("selectAgentFirst"),
        disabled: true,
      }];
  const sessionTextValue = intent === "resume" && (value === "auto" || value === "fresh") ? "" : value;

  useEffect(() => {
    if (inferredIntent !== "resume") setForcedIntent(null);
  }, [inferredIntent]);

  function switchIntent(next: "auto" | "fresh" | "resume") {
    if (next === "auto") {
      setForcedIntent(null);
      onChange("auto");
    } else if (next === "fresh") {
      setForcedIntent(null);
      onChange("fresh");
    } else {
      setForcedIntent("resume");
      if (matchingSessions[0]?.id) onChange(matchingSessions[0].id);
    }
  }

  return (
    <div className="rounded-lg border border-default bg-[var(--bg-card)] p-1.5">
      <div className="grid grid-cols-3 gap-1">
        {(["auto", "fresh", "resume"] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => switchIntent(option)}
            className={`min-h-8 rounded-md px-2 text-[11px] font-semibold transition-colors ${
              intent === option
                ? "bg-[var(--accent-bg)] text-[var(--accent)]"
                : "text-tertiary hover:bg-[var(--bg-hover)] hover:text-primary"
            }`}
            aria-pressed={intent === option}
          >
            {option === "auto" ? t("sessionAuto") : option === "fresh" ? t("sessionFresh") : t("sessionResume")}
          </button>
        ))}
      </div>

      {intent === "resume" ? (
        <div className="mt-1.5 flex items-center rounded-md border border-default bg-[var(--bg-card)] transition-all hover:border-[var(--border-strong)] focus-within:ring-2 focus-within:ring-[var(--accent-border)] focus-within:border-[var(--accent)]">
          <input
            type="text"
            value={sessionTextValue}
            onChange={(event) => onChange(event.target.value)}
            placeholder={
              displayAgent
                ? t("sessionIdPlaceholderWithAgent", { agent: displayAgent })
                : t("sessionIdPlaceholder")
            }
            className="min-w-0 flex-1 h-8 px-2.5 rounded-l-md text-[12px] bg-transparent placeholder:text-muted focus:outline-none"
          />
          <Dropdown
            align="right"
            value={matchingSessions.some((session) => session.id === value) ? value : ""}
            onChange={(nextValue) => {
              if (nextValue !== "__empty") onChange(nextValue);
            }}
            items={items}
            ariaLabel={t("sessionPicker")}
            className="shrink-0"
            triggerClassName="h-full block"
            trigger={
              <span className="h-8 min-w-8 px-2 border-l border-default text-tertiary hover:text-primary hover:bg-[var(--bg-hover)] rounded-r-md transition-colors flex items-center justify-center">
                <ChevronsUpDown className="w-3.5 h-3.5" />
              </span>
            }
          />
        </div>
      ) : (
        <p className="px-1.5 pt-1.5 text-[10px] leading-snug text-tertiary">
          {intent === "auto" ? t("sessionAutoHint") : t("sessionFreshHint")}
        </p>
      )}
    </div>
  );
}
