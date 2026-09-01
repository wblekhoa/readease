/** Product tab bar in the DS ToggleButtonGroup **style-2** geometry.
 *
 * Style 2 is the full-bleed one: the track carries no inner padding, so the
 * selected item fills it edge to edge and the rail's own radius clips the
 * corners. Style 1 (a smaller pill floating inside a padded track) is what
 * this used to be; the owner chose style 2 on 2026-09-01.
 *
 * Not the registry copy: `ui-registry/ToggleButtonGroup` is authored for the
 * DS's light-first web surfaces and carries hardcoded slate/white classes, so
 * on a dark-mode Mac it rendered a white rail inside a dark window. This
 * component keeps the canonical geometry but takes every colour from the
 * token bridge, which follows [data-theme]. Gap recorded in
 * docs/tauri-migration-plan.md - upstream candidate: a dark-capable variant.
 */
import { useRef, type KeyboardEvent } from "react";

export interface AppTab {
  value: string;
  label: string;
}

export function AppTabs({
  items,
  value,
  onChange,
  ariaLabel,
}: {
  items: readonly AppTab[];
  value: string;
  onChange: (next: string) => void;
  ariaLabel: string;
}) {
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const index = items.findIndex((item) => item.value === value);
    let next = index;
    if (event.key === "ArrowRight") next = Math.min(index + 1, items.length - 1);
    else if (event.key === "ArrowLeft") next = Math.max(index - 1, 0);
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = items.length - 1;
    else return;
    event.preventDefault();
    onChange(items[next].value);
    buttons.current[next]?.focus();
  };

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      onKeyDown={onKeyDown}
      className="inline-flex items-stretch overflow-hidden rounded-full bg-rail"
    >
      {items.map((item, index) => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            ref={(element) => {
              buttons.current[index] = element;
            }}
            type="button"
            aria-pressed={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(item.value)}
            className={
              "h-8 whitespace-nowrap rounded-full border px-4 text-sm font-semibold transition-colors " +
              (active
                ? "border-edge-strong bg-paper text-ink shadow-raised"
                : "border-transparent text-ink-mute hover:bg-wash hover:text-ink")
            }
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
