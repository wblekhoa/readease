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
      className="absolute bottom-[calc(var(--shell-bottom-h)+var(--layer-gap))] left-1/2 z-20 w-[26rem] max-w-[calc(100vw-3rem)] -translate-x-1/2 p-6 shadow-lifted"
    >
      <div className="flex items-center gap-2">
        <h3 className="m-0 flex-1 text-sm font-bold">{text("cost.title")}</h3>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>

      <GroupedSection className="mt-2">
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
          {spent > 0 && ` · ${text("cost.spent", { usd: formatUsd(spent) })}`}
        </Notice>
      )}
    </Surface>
  );
}
