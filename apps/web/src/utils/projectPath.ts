export function projectDirFromConfigPath(configPath: string): string {
  const path = configPath.trim();
  if (!path) return "";

  const nested = path.match(/^(.*)[\\/]\.cc-branch[\\/]config\.ya?ml$/);
  if (nested) return nested[1] || path;

  const lastSlash = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
  return lastSlash > 0 ? path.slice(0, lastSlash) : path;
}
