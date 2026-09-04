/** What a paid voice would cost this press of the button.
 *
 * The owner's rule for this feature (04/09): the figure goes IN the read
 * button, and the button stays disabled until there is one. So a person can
 * never spend money by pressing a button that had not yet told them the
 * price - which is the whole reason the estimate is exact rather than
 * indicative.
 *
 * The second rule is what is NOT here: "đừng hiện quá nhiều thông tin ra
 * ngoài". One number on the outside. Characters, credits, the session's
 * running total and the date the price was quoted all live behind the
 * settings button beside it.
 */

/** The engine's answer. `paid: false` is the local model - free, and the
 * button says nothing extra. */
export type Estimate =
  | { paid: false; chars: number; utterances: number; chapters: number }
  | {
      paid: true;
      provider: string;
      model: string;
      chars: number;
      utterances: number;
      chapters: number;
      usd: number;
      units: number;
      unit: "characters" | "credits";
      price_dated: string;
    };

/** How far one press reads. `null` chapters is the whole book, which is what
 * every reading did before paid voices existed. */
export const SCOPES: readonly (number | null)[] = [1, 2, 5, null];

const SCOPE_KEY = "readease.reading-scope";

export function storedScope(): number | null {
  try {
    const saved = localStorage.getItem(SCOPE_KEY);
    if (saved === "all") return null;
    const count = Number(saved);
    return SCOPES.includes(count) ? count : 1;
  } catch {
    // A reader who cannot remember the scope gets the cautious one, not the
    // expensive one: the default must never be "the whole book" by accident.
    return 1;
  }
}

export function rememberScope(chapters: number | null): void {
  try {
    localStorage.setItem(SCOPE_KEY, chapters === null ? "all" : String(chapters));
  } catch {
    // Forgetting it costs one click.
  }
}

/** True when this voice bills somebody. Paid voices are `provider:model:voice`
 * and the local catalogue never has two colons. */
export function isPaidVoice(voiceId: string): boolean {
  return voiceId.split(":").length >= 3;
}

/** The money, short enough to sit inside a button.
 *
 * Under a cent is real and must not round to "$0.00" - a reader who is told
 * zero and then charged has been misled, however small the sum. Above a
 * dollar the cents stop mattering next to the decision.
 */
export function formatUsd(usd: number): string {
  if (usd <= 0) return "$0";
  if (usd < 0.01) return "<$0,01";
  if (usd < 1) return `$${usd.toFixed(2).replace(".", ",")}`;
  return `$${usd.toFixed(2).replace(".", ",")}`;
}

/** Thousands the way Vietnamese writes them: 12.400. */
export function formatCount(value: number): string {
  return value.toLocaleString("vi-VN");
}

/** What the button carries, or "" for a voice that costs nothing. */
export function buttonCost(estimate: Estimate | null): string {
  if (estimate === null || !estimate.paid) return "";
  return formatUsd(estimate.usd);
}
