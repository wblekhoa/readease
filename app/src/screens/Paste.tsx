/** Paste text: a sheet to read from, not a form (owner, 21/10: "re-design
 * lại trang paste text được đẹp hơn").
 *
 * One centred column at the Reader's measure, the words on the paper with no
 * box around them - the page is the editor. Above it, the one line that
 * says where the text goes and the way into History; below it, the count and
 * what can be done with the text. An empty sheet says how to begin and
 * offers the last few pastes back; a translated one shows what is heard
 * under what was pasted (RE-PLAY-029).
 */
import type { ReactNode } from "react";
import { currentLanguage, text } from "../i18n";
import { Button, Textarea } from "../ui/controls";
import { ClipboardIcon } from "../ui/icons";
import { relativeDay } from "../ui/homeReading";
import { summarise } from "../ui/scanHistory";

const RECENT_LIMIT = 4;
const when = (at: number) => relativeDay(at, Date.now(), currentLanguage(), {
  today: text("home.today"), yesterday: text("home.yesterday"), daysAgo: days => text("home.days_ago", { days }),
});

export function Paste({ content, onChange, onClear, count, overLimit, translation, recents, onOpenRecent, onHistory, exportSlot }: {
  content: string;
  onChange: (value: string) => void;
  onClear: () => void;
  /** "54 / 100.000 ký tự", already in the reader's language. */
  count: string;
  overLimit: boolean;
  /** What is heard, when the paste is read in translation. */
  translation: { text: string; target: string } | null;
  /** Pastes kept in History, newest first: offered back on an empty sheet. */
  recents: readonly { at: number; text: string }[];
  onOpenRecent: (text: string) => void;
  onHistory: () => void;
  exportSlot: ReactNode;
}) {
  const empty = !content.trim();
  const language = text(translation?.target === "vi" ? "language.vi" : "language.en");
  return (
    <section className="shell-inset flex min-h-0 flex-1 flex-col">
      <div className="mx-auto flex min-h-0 w-full max-w-[72ch] flex-1 flex-col">
        <div className="flex items-center gap-3">
          <p className="m-0 min-w-0 flex-1 text-xs text-ink-mute">{text("paste.description")}</p>
          <Button variant="ghost" size="sm" data-popover-trigger onClick={onHistory}>{text("history.button")}</Button>
        </div>
        <Textarea
          plain
          aria-label={text("nav.paste")}
          /* Empty, the sheet is a few lines tall and what to do sits right
             under them; with words in it, it takes the page. */
          className={empty ? "mt-6 h-28 flex-none" : "mt-6 min-h-0 flex-1"}
          placeholder={text("paste.placeholder")}
          value={content}
          onChange={(event) => onChange(event.target.value)}
        />
        {empty && (
          <div className="min-h-0 flex-1 overflow-y-auto pb-4">
            <p className="m-0 text-xs text-ink-mute">{text("paste.empty_hint")}</p>
            {recents.length > 0 && (
              <div className="mt-5">
                <h2 className="m-0 mb-1 text-xs font-semibold uppercase tracking-wide text-ink-mute">{text("paste.recent")}</h2>
                <div className="-mx-3 flex flex-col">
                  {recents.slice(0, RECENT_LIMIT).map((entry) => {
                    const title = summarise(entry.text);
                    return (
                      <Button key={entry.at} variant="ghost" onClick={() => onOpenRecent(entry.text)}
                        aria-label={text("home.open_recent", { title })}
                        className="!h-auto w-full !justify-start gap-3 !rounded-2xl !px-3 !py-2 text-left">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center text-ink-mute [&_svg]:h-[18px] [&_svg]:w-[18px]"><ClipboardIcon /></span>
                        <span className="min-w-0 flex-1 truncate font-normal text-ink">{title}</span>
                        <span className="w-24 shrink-0 text-right text-xs text-ink-mute">{when(entry.at)}</span>
                      </Button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
        {translation && (
          /* A quiet band (owner, 21/10): paragraphs 8 px apart at 1.5. */
          <section aria-label={text("translation.translated", { language })}
            className="mt-3 flex max-h-[40%] min-h-0 flex-col rounded-2xl bg-band px-4 py-3">
            <p className="m-0 mb-1.5 text-xs font-semibold text-ink-mute">{text("translation.translated", { language })}</p>
            <div lang={translation.target} className="flex min-h-0 flex-col gap-2 overflow-y-auto">
              {translation.text.split(/\n\s*\n/).filter(part => part.trim()).map((part, index) => (
                <p key={index} className="m-0 break-words text-sm leading-[1.5] text-ink">{part.trim()}</p>
              ))}
            </div>
          </section>
        )}
        {/* Two things on one line - the count, and past the limit what to
            do - so a gap between them (27/09). */}
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-edge-alpha py-2.5 text-xs text-ink-mute">
          <span className={`tabular-nums ${overLimit ? "font-semibold text-danger" : ""}`}>{count}</span>
          {overLimit && <span className="font-medium text-danger">{text("paste.over_limit")}</span>}
          <span className="ml-auto flex items-center gap-2">
            {!empty && <Button variant="ghost" size="sm" onClick={onClear}>{text("paste.clear")}</Button>}
            {exportSlot}
          </span>
        </div>
      </div>
    </section>
  );
}
