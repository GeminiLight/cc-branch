import { FolderGit2, SquareTerminal } from "lucide-react";
import cursorIconUrl from "../../assets/agent-icons/cursor.svg";
import vscodeIconUrl from "../../assets/opener-icons/vscode.svg";
import warpIconUrl from "../../assets/opener-icons/warp.png";

function normalizeOpenerKey(openerId: string | null | undefined, label?: string): string {
  const value = `${openerId || ""} ${label || ""}`.toLowerCase();
  const compact = value.replace(/[\s_.-]+/g, "");
  if (compact.includes("cursor")) return "cursor";
  if (compact.includes("vscode") || compact.includes("visualstudiocode")) return "vscode";
  if (compact.includes("warp")) return "warp";
  if (compact.includes("filemanager") || compact.includes("finder") || compact.includes("explorer")) return "file-manager";
  if (compact.includes("terminal") || compact.includes("iterm")) return "terminal";
  return openerId || "opener";
}

export default function OpenerMark({
  openerId,
  label,
  compact = false,
}: {
  openerId?: string | null;
  label: string;
  compact?: boolean;
}) {
  const key = normalizeOpenerKey(openerId, label);
  const sizeClass = compact ? "h-5 w-5" : "h-6 w-6";
  const imageClass = compact ? "h-3.5 w-3.5" : "h-4 w-4";
  const iconClass = compact ? "h-3.5 w-3.5" : "h-4 w-4";
  const imageUrl = key === "cursor" ? cursorIconUrl : key === "vscode" ? vscodeIconUrl : key === "warp" ? warpIconUrl : null;

  return (
    <span
      className={`${sizeClass} inline-flex shrink-0 items-center justify-center overflow-hidden rounded-md border border-default bg-[var(--bg-card)] text-tertiary`}
      aria-label={`${label} logo`}
      title={label}
    >
      {imageUrl ? (
        <img src={imageUrl} alt="" className={`${imageClass} object-contain`} draggable={false} />
      ) : key === "file-manager" ? (
        <FolderGit2 className={iconClass} aria-hidden="true" />
      ) : (
        <SquareTerminal className={iconClass} aria-hidden="true" />
      )}
    </span>
  );
}
