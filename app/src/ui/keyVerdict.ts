/** Whether a provider key actually works, read out of the engine's reply.
 *
 * There are TWO `ok`s in that reply and they answer different questions.
 * The outer one is the envelope's: "the engine received this and answered".
 * The inner one, inside `result`, is the verdict: "the provider accepted
 * this key". Reading the outer one called every key good - a key the
 * provider had just rejected included, because the engine answered that
 * refusal perfectly well (owner, 05/09).
 *
 * The reply can also be nothing at all: `saveKey` catches a failed request
 * into `null`, and a key that could not be checked is not a key that works.
 */

export type KeyVerdict = { ok: boolean; code: string | null };

export type KeyReply = { result?: { ok?: boolean; code?: string } } | null | undefined;

export function keyVerdict(reply: KeyReply): KeyVerdict {
  const verdict = reply?.result;
  if (!verdict) return { ok: false, code: "network" };
  return { ok: verdict.ok === true, code: verdict.code ?? null };
}
