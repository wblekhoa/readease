/** Where a provider's key is given, and the only place it is ever typed.
 *
 * One row per provider, saying whether a key is there - never what it is.
 * The engine answers `config.get` for these with `{value: null, set: true}`
 * on purpose (server.py `_SECRET_CONFIG_KEYS`), so this component could not
 * display a stored key even if it wanted to. What it shows is the fact.
 *
 * Saving CHECKS: the key goes down, the catalogue is asked again, and a
 * provider that returns no voices has not been set up, whatever the key
 * looked like. Being told at the moment of typing beats being told later,
 * mid-chapter, in the middle of a reading somebody was waiting for.
 */
import { useState } from "react";
import { text } from "../i18n";
import { Button, Input, Notice } from "./controls";
import { GroupedRow, GroupedSection } from "./patterns";
import { PROVIDERS } from "./readingCost";

export function ProviderKeys({
  title,
  keysSet,
  onSaveKey,
}: {
  title?: string;
  /** Provider id → whether a key is stored. Never the key itself. */
  keysSet: Record<string, boolean>;
  /** Saves, then reports whether the provider actually answered. */
  onSaveKey: (provider: string, key: string) => Promise<boolean>;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [refused, setRefused] = useState<string | null>(null);

  const start = (provider: string) => {
    setEditing(provider);
    setDraft("");
    setRefused(null);
  };

  const save = async (provider: string) => {
    setBusy(true);
    setRefused(null);
    try {
      const ok = await onSaveKey(provider, draft.trim());
      if (ok) {
        setEditing(null);
        setDraft("");
      } else {
        setRefused(provider);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <GroupedSection title={title}>
      {PROVIDERS.map((provider) => (
        editing === provider.id ? (
          <div key={provider.id} className="flex flex-col gap-2 py-3.5">
            <div className="text-sm font-medium">{provider.label}</div>
            <div className="flex items-center gap-2">
              <Input
                type="password"
                autoFocus
                value={draft}
                disabled={busy}
                placeholder={text("key.placeholder")}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && draft.trim()) void save(provider.id);
                  if (event.key === "Escape") setEditing(null);
                }}
                className="min-w-0 flex-1"
              />
              <Button
                size="sm"
                variant="primary"
                disabled={busy || !draft.trim()}
                onClick={() => void save(provider.id)}
              >
                {busy ? text("key.checking") : text("key.save")}
              </Button>
              <Button size="sm" disabled={busy} onClick={() => setEditing(null)}>
                {text("key.cancel")}
              </Button>
            </div>
            {refused === provider.id && (
              <Notice tone="error">{text("key.refused")}</Notice>
            )}
          </div>
        ) : (
          <GroupedRow
            key={provider.id}
            title={provider.label}
            subtitle={keysSet[provider.id] ? text("key.set") : text("key.unset")}
            trailing={
              <Button size="sm" onClick={() => start(provider.id)}>
                {keysSet[provider.id] ? text("key.change") : text("key.add")}
              </Button>
            }
          />
        )
      ))}
    </GroupedSection>
  );
}
