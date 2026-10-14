/** Naming the file an export is saved as. Pure, so it can be tested. */

/** The name the save panel proposes: the app and the day, never the text -
 * the first words of a pasted passage may be anything at all. */
export function defaultExportName(now: Date = new Date()): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `ReadEase ${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}.${pad(now.getMinutes())}.wav`;
}

/** A chosen path that ends in `.wav` - the panel lets a name lose it. */
export function asWavPath(path: string): string {
  return /\.wav$/i.test(path) ? path : `${path}.wav`;
}
