/** Small shared boundary rules for book exports, before any work is queued. */
export function chapterRange(first: number, last: number, count: number) {
  return Number.isInteger(first) && Number.isInteger(last) && first >= 1 && last >= first && last <= count
    ? { fromChapter: first - 1, chapters: last - first + 1 } : null;
}
export function audiobookName(title: string): string {
  return `${title.replace(/[/:\\\x00-\x1f]+/g, " ").replace(/\s+/g, " ").trim().slice(0, 160) || "ReadEase"}.m4b`;
}
export type ExportPhase = "synthesising" | "normalising" | "encoding";
export type Progress = { done: number; total: number; phase?: string };
export function progressFor<T extends { kind: string }>(job: T, progress: Progress): T {
  if (job.kind !== "running") return job;
  const phase: ExportPhase = progress.phase === "normalising" || progress.phase === "encoding" ? progress.phase : "synthesising";
  return { ...job, done: progress.done, total: progress.total, phase };
}
