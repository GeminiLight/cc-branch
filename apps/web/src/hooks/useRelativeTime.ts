import { useState, useEffect } from "react";

export function useRelativeTime(timestamp: number | null): string {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!timestamp) return;
    const update = () => setNow(Date.now());
    update();
    const iv = setInterval(update, 30000); // update every 30s
    return () => clearInterval(iv);
  }, [timestamp]);

  if (!timestamp) return "--";

  const diffMs = now - timestamp;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 10) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  return `${diffDay}d ago`;
}
