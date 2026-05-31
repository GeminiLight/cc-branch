import { useCallback, useEffect, useMemo, useState } from "react";
import YAML from "js-yaml";
import { AlertTriangle, AppWindow, ChevronDown, Loader2, Plus, RotateCcw, Save, Trash2 } from "lucide-react";
import { APIRequestError } from "../api/client";
import type { APIClient } from "../api/client";
import type { OpenerConfigInfo } from "../types";
import { useI18n } from "../i18n";
import { useToast } from "./ui/Toast";
import { FieldLabel, SelectInput, TextInput } from "./ConfigEditor/FormPrimitives";

type GlobalOpenerConfig = {
  label: string;
  kind: "terminal" | "editor";
  command: string;
  args: string[];
  capabilities: string[];
};

const DEFAULT_OPENER: GlobalOpenerConfig = {
  label: "",
  kind: "terminal",
  command: "",
  args: [],
  capabilities: [],
};

function openersFromPayload(items: OpenerConfigInfo[]): Record<string, GlobalOpenerConfig> {
  return Object.fromEntries(
    items.map((opener) => [
      opener.id,
      {
        label: opener.label || opener.id,
        kind: opener.kind === "editor" ? "editor" : "terminal",
        command: opener.command || opener.id,
        args: Array.isArray(opener.args) ? opener.args : [],
        capabilities: Array.isArray(opener.capabilities) ? opener.capabilities : [],
      },
    ])
  );
}

function cleanOpener(opener: GlobalOpenerConfig): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (opener.label) out.label = opener.label;
  out.kind = opener.kind;
  if (opener.command) out.command = opener.command;
  if (opener.args.length > 0) out.args = opener.args;
  if (opener.capabilities.length > 0) out.capabilities = opener.capabilities;
  return out;
}

export function serializeGlobalOpeners(openers: Record<string, GlobalOpenerConfig>): string {
  const out: Record<string, unknown> = { openers: {} };
  for (const [name, opener] of Object.entries(openers)) {
    (out.openers as Record<string, unknown>)[name] = cleanOpener(opener);
  }
  return YAML.dump(out, {
    indent: 2,
    lineWidth: -1,
    noRefs: true,
    sortKeys: false,
  });
}

function nextOpenerName(openers: Record<string, GlobalOpenerConfig>): string {
  const names = new Set(Object.keys(openers));
  const preferred = ["ghostty", "wezterm", "zed", "sublime"].find((name) => !names.has(name));
  if (preferred) return preferred;
  let index = Object.keys(openers).length + 1;
  while (names.has(`opener-${index}`)) index += 1;
  return `opener-${index}`;
}

function OpenerCard({
  name,
  opener,
  expanded,
  onToggle,
  onPatch,
  onRename,
  onDelete,
}: {
  name: string;
  opener: GlobalOpenerConfig;
  expanded: boolean;
  onToggle: () => void;
  onPatch: (patch: Partial<GlobalOpenerConfig>) => void;
  onRename: (name: string) => boolean;
  onDelete: () => void;
}) {
  const { t } = useI18n();
  const [draftName, setDraftName] = useState(name);
  const argsText = opener.args.join(" ");

  useEffect(() => {
    setDraftName(name);
  }, [name]);

  function commitName() {
    const next = draftName.trim();
    if (next === name) return;
    if (!onRename(next)) setDraftName(name);
  }

  return (
    <div className="rounded-md border border-default bg-[var(--bg-card)]">
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          onClick={onToggle}
          className="flex-1 min-w-0 text-left rounded-md hover:surface-hover transition-colors px-1.5 py-1 flex items-center gap-2"
        >
          <ChevronDown className={`w-3.5 h-3.5 text-tertiary shrink-0 transition-transform ${expanded ? "" : "-rotate-90"}`} />
          <AppWindow className="w-3.5 h-3.5 text-tertiary shrink-0" />
          <span className="min-w-0">
            <span className="block text-[13px] font-semibold text-primary truncate">{opener.label || name}</span>
            <span className="block text-[11px] text-tertiary truncate">{opener.command || t("customOpener")}</span>
          </span>
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="icon-touch rounded-md text-tertiary hover:text-primary hover:bg-[var(--bg-hover)] flex items-center justify-center"
          aria-label={t("removeOpenerNamed", { name })}
          title={t("removeOpenerNamed", { name })}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {expanded && (
        <div className="px-3 pb-3 pt-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <FieldLabel required>{t("openerId")}</FieldLabel>
            <TextInput
              value={draftName}
              onChange={setDraftName}
              ariaLabel={t("openerId")}
              onBlur={commitName}
              onKeyDown={(event) => {
                if (event.key === "Enter") event.currentTarget.blur();
              }}
              invalid={!draftName.trim()}
            />
          </div>
          <div>
            <FieldLabel>{t("label")}</FieldLabel>
            <TextInput value={opener.label} onChange={(value) => onPatch({ label: value })} ariaLabel={t("label")} placeholder="Ghostty" />
          </div>
          <div>
            <FieldLabel>{t("kind")}</FieldLabel>
            <SelectInput
              value={opener.kind}
              onChange={(value) => onPatch({ kind: value === "editor" ? "editor" : "terminal" })}
              ariaLabel={t("kind")}
              options={[
                { value: "terminal", label: t("terminal") },
                { value: "editor", label: t("editor") },
              ]}
            />
          </div>
          <div>
            <FieldLabel required>{t("command")}</FieldLabel>
            <TextInput value={opener.command} onChange={(value) => onPatch({ command: value })} ariaLabel={t("command")} placeholder="ghostty" />
          </div>
          <div className="sm:col-span-2">
            <FieldLabel>{t("arguments")}</FieldLabel>
            <TextInput
              value={argsText}
              onChange={(value) => onPatch({ args: value.trim() ? value.trim().split(/\s+/) : [] })}
              ariaLabel={t("arguments")}
              placeholder="--working-directory {cwd}"
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default function GlobalOpenersSettings({ api }: { api: APIClient }) {
  const { t } = useI18n();
  const toast = useToast();
  const [path, setPath] = useState("");
  const [openers, setOpeners] = useState<Record<string, GlobalOpenerConfig>>({});
  const [initialContent, setInitialContent] = useState("");
  const [baseMtime, setBaseMtime] = useState<number | null | undefined>(null);
  const [baseHash, setBaseHash] = useState<string | undefined>(undefined);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const content = useMemo(() => serializeGlobalOpeners(openers), [openers]);
  const dirty = content !== initialContent;

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    api
      .getGlobalOpeners()
      .then((data) => {
        const parsed = openersFromPayload(data.user_openers ?? []);
        setOpeners(parsed);
        setInitialContent(serializeGlobalOpeners(parsed));
        setPath(data.path);
        setBaseMtime(data.mtime);
        setBaseHash(data.content_hash);
        setExpanded(Object.keys(parsed)[0] ?? null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, [api]);

  useEffect(() => {
    load();
  }, [load]);

  function addOpener() {
    const name = nextOpenerName(openers);
    setOpeners((current) => ({
      ...current,
      [name]: { ...DEFAULT_OPENER, label: name.charAt(0).toUpperCase() + name.slice(1), command: name },
    }));
    setExpanded(name);
  }

  function patchOpener(name: string, patch: Partial<GlobalOpenerConfig>) {
    setOpeners((current) => ({
      ...current,
      [name]: { ...current[name], ...patch },
    }));
  }

  function renameOpener(from: string, toRaw: string): boolean {
    const to = toRaw.trim();
    if (!to) {
      setError(t("openerIdRequired"));
      return false;
    }
    if (to !== from && openers[to]) {
      setError(t("openerAlreadyExists", { name: to }));
      return false;
    }
    setOpeners((current) => {
      const next: Record<string, GlobalOpenerConfig> = {};
      for (const [name, opener] of Object.entries(current)) {
        next[name === from ? to : name] = name === from && opener.command === from
          ? { ...opener, command: to }
          : opener;
      }
      return next;
    });
    setExpanded(to);
    setError("");
    return true;
  }

  function deleteOpener(name: string) {
    setOpeners((current) => {
      const next = { ...current };
      delete next[name];
      return next;
    });
    if (expanded === name) setExpanded(null);
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      const result = await api.saveGlobalOpeners(content, baseMtime, baseHash);
      const parsed = openersFromPayload(result.user_openers ?? []);
      setOpeners(parsed);
      setInitialContent(serializeGlobalOpeners(parsed));
      setPath(result.path);
      setBaseMtime(result.mtime);
      setBaseHash(result.content_hash);
      toast.success(t("globalOpenersSaved"));
    } catch (err: unknown) {
      const message = err instanceof APIRequestError || err instanceof Error ? err.message : String(err);
      setError(message);
      toast.error(message);
    } finally {
      setSaving(false);
    }
  }

  async function resetToDefaults() {
    setSaving(true);
    setError("");
    try {
      const result = await api.saveGlobalOpeners("openers: {}\n", baseMtime, baseHash);
      const parsed = openersFromPayload(result.user_openers ?? []);
      setOpeners(parsed);
      setInitialContent(serializeGlobalOpeners(parsed));
      setPath(result.path);
      setBaseMtime(result.mtime);
      setBaseHash(result.content_hash);
      setExpanded(null);
      toast.success(t("globalOpenersReset"));
    } catch (err: unknown) {
      const message = err instanceof APIRequestError || err instanceof Error ? err.message : String(err);
      setError(message);
      toast.error(message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section>
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <AppWindow className="w-3.5 h-3.5 shrink-0 text-tertiary" />
          <h4 className="text-[12px] font-semibold text-primary">{t("globalOpeners")}</h4>
        </div>
        <button
          type="button"
          onClick={addOpener}
          className="h-8 px-2.5 rounded-md bg-[var(--accent)] text-white text-[12px] font-medium flex items-center gap-1.5 disabled:opacity-50"
          disabled={loading}
        >
          <Plus className="w-3.5 h-3.5" />
          {t("addOpener")}
        </button>
      </div>
      {path && <p className="mb-2 truncate font-mono text-[11px] text-tertiary" title={path}>{path}</p>}

      {loading ? (
        <div className="h-28 rounded-md border border-default bg-[var(--bg-page)] flex items-center justify-center text-tertiary">
          <Loader2 className="w-4 h-4 animate-spin" />
        </div>
      ) : (
        <div className="space-y-2 max-h-[45vh] overflow-y-auto pr-1">
          {Object.entries(openers).map(([name, opener]) => (
            <OpenerCard
              key={name}
              name={name}
              opener={opener}
              expanded={expanded === name}
              onToggle={() => setExpanded((current) => current === name ? null : name)}
              onPatch={(patch) => patchOpener(name, patch)}
              onRename={(nextName) => renameOpener(name, nextName)}
              onDelete={() => deleteOpener(name)}
            />
          ))}
          {Object.keys(openers).length === 0 && (
            <div className="text-center py-6 border border-dashed border-default rounded-md">
              <AppWindow className="w-5 h-5 text-tertiary mx-auto mb-1.5" />
              <p className="text-[12px] text-secondary">{t("noOpenersYet")}</p>
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="mt-2 rounded-md border border-[var(--danger)]/20 danger-bg px-2.5 py-2 text-[12px] text-primary flex items-start gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-[var(--danger)] mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex items-center justify-end gap-2 mt-2">
        <button
          type="button"
          onClick={load}
          disabled={!dirty || loading || saving}
          className="h-8 px-3 rounded text-[12px] font-medium text-secondary hover:text-primary surface-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          {t("revert")}
        </button>
        <button
          type="button"
          onClick={resetToDefaults}
          disabled={loading || saving}
          className="h-8 px-3 rounded text-[12px] font-medium text-secondary hover:text-primary surface-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {t("resetToDefaults")}
        </button>
        <button
          type="button"
          onClick={save}
          disabled={!dirty || loading || saving}
          className="h-8 px-3 rounded text-[12px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
          {t("save")}
        </button>
      </div>
    </section>
  );
}
