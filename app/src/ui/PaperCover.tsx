/** Direction A, "Trang giấy" (owner, 23/10): a document without artwork is
 * drawn as a sheet of tinted paper - its format at the head, its title in
 * the app's own sans (no serif, owner's call), the first chapter names the
 * way a page would show them, and a folded corner that says "paper, not a
 * book". The tint comes from `paperHues` (stable, never twinned). */
import { text } from "../i18n";
import type { PaperHue } from "./paperTint";

export function PaperCover({ hue, title, format, chapters, chapterTitles }: {
  hue: PaperHue;
  title: string;
  format: string;
  chapters: number;
  chapterTitles: readonly string[];
}) {
  const paper = `var(--fill-${hue}-matte)`;
  const ink = `var(--text-color-${hue}-stress)`; // -bold measured 4.3:1 at 11px; -stress holds 4.5:1+
  const haze = `var(--fill-${hue}-haze)`;
  return (
    <div data-paper-cover={hue}
      className="relative flex aspect-[2/3] w-full flex-col overflow-hidden rounded-lg p-3 shadow-raised transition-shadow group-hover:shadow-lifted"
      style={{ background: paper }}>
      {/* The folded corner: a triangle of the paper's own haze. */}
      <span aria-hidden className="absolute right-0 top-0 h-6 w-6"
        style={{ background: haze, clipPath: "polygon(0 0, 100% 100%, 0 100%)" }} />
      <span className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: ink }}>{format}</span>
      <span className="mt-2 line-clamp-4 break-words text-[15px] font-semibold leading-snug text-ink">{title}</span>
      {chapterTitles.length > 0 ? (
        <ol className="m-0 mt-3 flex list-none flex-col gap-1 p-0">
          {chapterTitles.slice(0, 4).map((name, index) => (
            <li key={index} className="flex min-w-0 gap-1.5 text-[11px] leading-snug text-ink-mute">
              <span className="shrink-0 tabular-nums" style={{ color: ink }}>{index + 1}</span>
              <span className="min-w-0 truncate">{name}</span>
            </li>
          ))}
        </ol>
      ) : (
        /* No chapters to name: a few ruled lines, the page it would be. */
        <span aria-hidden className="mt-3 flex flex-col gap-1.5">
          {[92, 84, 88, 60].map((width, index) => (
            <span key={index} className="h-1 rounded-full" style={{ width: `${width}%`, background: haze }} />
          ))}
        </span>
      )}
      {chapters > 0 && (
        <span className="mt-auto text-[11px] text-ink-mute">{text("library.chapter_count", { count: chapters })}</span>
      )}
    </div>
  );
}
