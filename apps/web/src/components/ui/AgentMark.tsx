import claudeIconUrl from "../../assets/agent-icons/claude.svg";
import cursorIconUrl from "../../assets/agent-icons/cursor.svg";
import geminiIconUrl from "../../assets/agent-icons/gemini.svg";
import kimiIconUrl from "../../assets/agent-icons/kimi.svg";
import openaiIconUrl from "../../assets/agent-icons/openai.svg";

export function displayAgentName(agent: string | null | undefined): string {
  return agent ? agent.charAt(0).toUpperCase() + agent.slice(1) : "";
}

export function normalizeAgentKey(agent: string | null | undefined): string {
  const value = (agent || "").toLowerCase();
  const compact = value.replace(/[\s_-]+/g, "");
  if (value.includes("codex")) return "codex";
  if (compact.includes("claude") || compact.includes("cloudcode") || compact.includes("anthropic")) return "claude";
  if (compact.includes("gemini") || compact.includes("antigravity")) return "gemini";
  if (compact.includes("cursor")) return "cursor";
  if (compact.includes("kimi")) return "kimi";
  return value;
}

function agentIdentity(agent: string | null | undefined) {
  const key = normalizeAgentKey(agent);
  if (key === "codex") return { label: "Codex", initials: "Cx", iconUrl: openaiIconUrl, tone: "bg-white text-zinc-950 border-zinc-200 dark:bg-zinc-100 dark:text-zinc-950 dark:border-zinc-300" };
  if (key === "claude") return { label: "Claude", initials: "Cl", iconUrl: claudeIconUrl, tone: "bg-[#f4eee7] text-[#8a4b25] border-[#dfcabc] dark:bg-[#2a1d17] dark:text-[#f2c6a4] dark:border-[#5f3b2a]" };
  if (key === "gemini") return { label: "Gemini", initials: "G", iconUrl: geminiIconUrl, tone: "bg-[#eef4ff] text-[#2459c7] border-[#c8d9ff] dark:bg-[#101a2e] dark:text-[#9bbcff] dark:border-[#293d66]" };
  if (key === "cursor") return { label: "Cursor", initials: "Cu", iconUrl: cursorIconUrl, tone: "bg-zinc-950 text-white border-zinc-800 dark:bg-zinc-100 dark:text-zinc-950 dark:border-zinc-300" };
  if (key === "kimi") return { label: "Kimi", initials: "Ki", iconUrl: kimiIconUrl, tone: "bg-[#f2efff] text-[#5d48b1] border-[#d7cff7] dark:bg-[#191329] dark:text-[#c8bbff] dark:border-[#3e3268]" };
  if (agent) {
    const label = displayAgentName(agent);
    return {
      label,
      initials: label.slice(0, 2) || "A",
      tone: "bg-[var(--bg-elevated)] text-secondary border-default",
    };
  }
  return { label: "Shell", initials: "$", tone: "bg-[var(--accent-bg)] text-[var(--accent)] border-[var(--accent-border)]" };
}

export default function AgentMark({ agent, compact = false }: { agent?: string | null; compact?: boolean }) {
  const identity = agentIdentity(agent);
  const sizeClass = compact ? "h-5 w-5" : "h-6 w-6";
  return (
    <span
      className={`${sizeClass} inline-flex shrink-0 items-center justify-center overflow-hidden rounded-md border font-bold tracking-[-0.02em] ${compact ? "text-[9px]" : "text-[10px]"} ${identity.tone}`}
      title={identity.label}
      aria-label={identity.label}
    >
      {"iconUrl" in identity && identity.iconUrl ? (
        <img src={identity.iconUrl} alt="" className={`${compact ? "h-3.5 w-3.5" : "h-4 w-4"} object-contain`} draggable={false} />
      ) : (
        identity.initials
      )}
    </span>
  );
}
