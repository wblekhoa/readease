/** Everything about what a paid voice costs, EXCEPT the one number.
 *
 * The owner's shape for this (04/09): the money goes in the read button, and
 * a settings button beside it opens the rest - "đừng hiện quá nhiều thông
 * tin ra ngoài, nếu cần thì ẩn chúng đi". So the outside of the app carries
 * a figure and nothing else, and the characters, the credits, the ceiling,
 * the running total and the day the price was quoted all live in here,
 * one press away, for the moment somebody actually wants them.
 *
 * It opens ABOVE the footer like the settings panel, and closes on Escape
 * the same way - a floating layer in this app behaves the same wherever it
 * came from.
 */
import { useEffect } from "react";
import { text } from "../i18n";
import { IconButton, Notice, Select, Surface } from "./controls";
import { GroupedRow, GroupedSection } from "./patterns";
import { CloseIcon } from "./icons";
import { SCOPES, formatCount, formatUsd, type Estimate } from "./readingCost";

/** The ceilings offered. Not a free-text box: a number typed into a money
 * field is a way to mistype a decimal point, and every one of these is a
 * sum somebody would not mind losing. */
const BUDGETS: readonly (number | null)[] = [0.25, 1, 5, null];

/** How far one press reads, and where the money stops.
 *
 * Two settings, deliberately in TWO places: beside the read button, where
 * the price is, and inside the voice panel's API tab, where the key and the
 * voice are (owner, 04/09 - "để user tiện lợi có thể điều chỉnh ở nhiều nơi
 * khác nhau"). One component, so the two places can never drift into two
 * different behaviours - which is the usual cost of putting a control in two
 * places, and the reason to pay it once here instead.
 *
 * Both persist: the scope in localStorage, the ceiling in the engine's
 * settings file. Closing the panel or quitting the app changes neither.
 */
export function ReadingLimits({
  scope,
  budget,
  spent,
  onScope,
  onBudget,
  className = "",
}: {
  scope: number | null;
  budget: number | null;
  /** Dollars run up since the app opened - context for the ceiling. */
  spent: number;
  onScope: (chapters: number | null) => void;
  onBudget: (usd: number | null) => void;
  className?: string;
}) {
  return (
    <GroupedSection className={className}>
      <GroupedRow
        title={text("cost.scope")}
        trailing={
          <Select
            value={scope === null ? "all" : String(scope)}
            onChange={(event) =>
              onScope(event.target.value === "all" ? null : Number(event.target.value))
            }
          >
            {SCOPES.map((chapters) => (
              <option key={chapters ?? "all"} value={chapters === null ? "all" : chapters}>
                {chapters === null
                  ? text("cost.scope_all")
                  : chapters === 1
                    ? text("cost.scope_one")
                    : text("cost.scope_chapters", { count: chapters })}
              </option>
            ))}
          </Select>
        }
      />
      <GroupedRow
        title={text("cost.budget")}
        /* The running total sits under the ceiling it is running towards -
           a limit with no sense of how close you are is half a limit. */
        subtitle={spent > 0 ? text("cost.spent", { usd: formatUsd(spent) }) : undefined}
        trailing={
          <Select
            value={budget === null ? "off" : String(budget)}
            onChange={(event) =>
              onBudget(event.target.value === "off" ? null : Number(event.target.value))
            }
          >
            {BUDGETS.map((usd) => (
              <option key={usd ?? "off"} value={usd === null ? "off" : usd}>
                {usd === null ? text("cost.budget_off") : formatUsd(usd)}
              </option>
            ))}
          </Select>
        }
      />
    </GroupedSection>
  );
}

export function CostPanel({
  estimate,
  failed,
  scope,
  budget,
  spent,
  onScope,
  onBudget,
  onClose,
}: {
  /** null while the engine is still counting. */
  estimate: Estimate | null;
  /** The count did not come back at all - a different thing from "not yet". */
  failed: boolean;
  scope: number | null;
  budget: number | null;
  /** Dollars run up since the app opened. */
  spent: number;
  onScope: (chapters: number | null) => void;
  onBudget: (usd: number | null) => void;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const paid = estimate?.paid === true;

  return (
    <Surface
      edge="strong"
      radius="sheet"
      className="absolute bottom-[calc(var(--shell-bottom-inner)+var(--layer-gap))] left-1/2 z-20 w-[26rem] max-w-[calc(100vw-3rem)] -translate-x-1/2 p-6 shadow-lifted"
    >
      <div className="flex items-center gap-2">
        <h3 className="m-0 flex-1 text-sm font-bold">{text("cost.title")}</h3>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>

      <ReadingLimits
        scope={scope}
        budget={budget}
        spent={spent}
        onScope={onScope}
        onBudget={onBudget}
        className="mt-2"
      />

      {/* The detail the button deliberately does not carry. */}
      <Notice tone={failed ? "error" : "ok"} className="mt-3 block">
        {failed
          ? text("cost.failed")
          : estimate === null
          ? text("cost.measuring")
          : !paid
            ? text("cost.free")
            : text("cost.detail", {
                chars: formatCount(estimate.chars),
                chapters: estimate.chapters,
                date: estimate.price_dated,
              })}
      </Notice>
      {paid && estimate?.paid && (
        <Notice className="mt-1 block">
          {text("cost.units", {
            units: formatCount(estimate.units),
            unit: text(
              estimate.unit === "credits" ? "cost.unit_credits" : "cost.unit_characters",
            ),
          })}
        </Notice>
      )}
    </Surface>
  );
}
