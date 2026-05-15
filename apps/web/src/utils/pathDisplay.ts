export function pathSegments(path: string): string[] {
  return path.trim().split(/[\\/]+/).filter(Boolean);
}

export function pathBasename(path: string): string {
  const segments = pathSegments(path);
  return segments.at(-1) || path.trim();
}

export function compactPathTail(path: string, count = 3): string {
  const segments = pathSegments(path);
  if (segments.length === 0) return "";
  return segments.slice(-count).join("/");
}
