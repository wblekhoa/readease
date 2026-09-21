/** The cover for Now Playing, as the host wants it (HIG 3.19).
 *
 * `now_playing` fires on every state change and a cover is 100-200 KB, so
 * the bytes travel once per document: the first payload for a key carries
 * them, every later one carries the key alone and the host answers from
 * what it kept. Pure, so the node runner can pin the rule.
 */

export type ArtworkPayload = { key: string; data?: string };

/** What to send for `key` given the cover's data URL and the key whose
 * bytes the host already holds. `null` when there is nothing to show -
 * no cover, or one that is not a base64 data URL. */
export function artworkPayload(
  key: string,
  cover: string | null | undefined,
  sentKey: string | null,
): ArtworkPayload | null {
  if (!cover) return null;
  const match = /^data:[^;,]+;base64,([A-Za-z0-9+/=]+)$/.exec(cover);
  if (!match) return null;
  return sentKey === key ? { key } : { key, data: match[1] };
}
