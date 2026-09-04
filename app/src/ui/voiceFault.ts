/** What a failed reading actually was, in a word the interface can say.
 *
 * The engine names its failures - it has to, because "something went wrong"
 * is useless to somebody mid-chapter who has just been charged, while "the
 * key was refused", "you are out of credit" and "the network dropped" lead
 * to three different next actions. Eight sentences were written for those
 * eight names and then never reached a screen: the footer printed the raw
 * engine string, truncated, and the reader saw `voice_failed: quota: You
 * exceeded...` where `voiceerr.quota` was waiting to say it in their own
 * language.
 *
 * Two prefixes, because there are two moments a paid reading can stop:
 *
 *   `voice_unavailable: <reason>`  before anything was sent - no key, or our
 *                                  own ceiling. Nothing was charged.
 *   `voice_failed: <code>: <text>` the provider was asked and said no.
 *
 * Parsed rather than matched exactly: the string arrives through Tauri's
 * error channel, which wraps it, so the code is looked for INSIDE whatever
 * came back. An unrecognised failure keeps its raw text - a local engine
 * fault is still a real fault and must not be dressed up as a voice one.
 */

export const FAULT_CODES = [
  "no_key",
  "bad_key",
  "quota",
  "rate_limit",
  "network",
  "provider_down",
  "refused",
  "budget",
] as const;

export type FaultCode = (typeof FAULT_CODES)[number];

export type Fault = {
  /** The named failure, when this was one. */
  code: FaultCode | null;
  /** What the engine said, kept for the cases nothing is named for. */
  raw: string;
};

const PREFIX = /(?:voice_failed|voice_unavailable):\s*([a-z_]+)/;

export function readingFault(raw: string): Fault {
  const found = PREFIX.exec(raw);
  const word = found?.[1];
  const code = FAULT_CODES.find((known) => known === word) ?? null;
  return { code, raw };
}

/** The i18n key for a fault, or null when there is no sentence for it.
 *
 * Typed as the literal key rather than `string` so `text()` still checks it:
 * a code added here without a sentence written for it is a build error, not
 * a blank line in front of a reader. */
export function faultKey(fault: Fault): `voiceerr.${FaultCode}` | null {
  return fault.code ? `voiceerr.${fault.code}` : null;
}
