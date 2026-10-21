/** Paste text: a sheet to read from, not a form (owner, 21/10: "re-design
 * lại trang paste text được đẹp hơn").
 *
 * One centred column at the Reader's measure. Above, the one line that says
 * where the text goes and the way into History; then the sheet the words go
 * on, carrying their count and Clear. Reading and exporting them are the
 * bottom bar's (21/10). An empty sheet says how to begin and offers the last
 * few pastes back; a translated one shows what is heard under what was
 * pasted (RE-PLAY-029).
 */
import { currentLanguage, text } from "../i18n";
import { Button, Textarea } from "../ui/controls";
import { ClipboardIcon } from "../ui/icons";
import { relativeDay } from "../ui/homeReading";
import { summarise } from "../ui/scanHistory";

const RECENT_LIMIT = 4;
const when = (at: number) => relativeDay(at, Date.now(), currentLanguage(), {
  today: text("home.today"), yesterday: text("home.yesterday"), daysAgo: days => text("home.days_ago", { days }),
});

export function Paste({ content, onChange, onClear, count, overLimit, translation, recents, onOpenRecent, onHistory }: {
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
}) {
  const empty = !content.trim();
  const language = text(translation?.target === "vi" ? "language.vi" : "language.en");
  return (
    <section className="shell-inset flex min-h-0 flex-1 flex-col">
      <div className="mx-auto flex min-h-0 w-full max-w-[72ch] flex-1 flex-col">
        <div className="flex items-center gap-3">
          <p className="m-0 min-w-0 flex-1 text-xs text-ink-mute">{text("paste.description")}</p>
          {/* The ghost button pads its label: pulled out by that padding, the
              word lines up with the column's right edge like the dates below. */}
          <Button variant="ghost" size="sm" data-popover-trigger onClick={onHistory} className="-mr-2.5">{text("history.button")}</Button>
        </div>
        {/* The sheet: a page of its own colour, so where the words go is
            plain before a word is in it (owner, 21/10: "phần input đang hơi
            khó nhìn"). What belongs to the words rides on it - what is heard
            when they are read in translation - while what to
            DO with them sits in the bottom bar beside Read. With words in
            it, it takes the page; the line under it keeps room for the
            "Reading…" capsule over the transport. */}
        <div className={`mt-4 flex flex-col rounded-2xl bg-band px-5 pt-4 ${empty ? "flex-none pb-4" : "min-h-0 flex-1 pb-4"}`}>
          <Textarea
            plain
            aria-label={text("nav.paste")}
            className={empty ? "h-28 flex-none" : "min-h-0 flex-1"}
            placeholder={text("paste.placeholder")}
            value={content}
            onChange={(event) => onChange(event.target.value)}
          />
          {translation && (
            /* Paragraphs 8 px apart at 1.5 (owner, 21/10), under a hairline. */
            <section aria-label={text("translation.translated", { language })}
              className="mt-3 flex max-h-[40%] min-h-0 flex-col border-t border-edge-alpha pt-3">
              <p className="m-0 mb-1.5 text-xs font-semibold text-ink-mute">{text("translation.translated", { language })}</p>
              <div lang={translation.target} className="flex min-h-0 flex-col gap-2 overflow-y-auto">
                {translation.text.split(/\n\s*\n/).filter(part => part.trim()).map((part, index) => (
                  <p key={index} className="m-0 break-words text-sm leading-[1.5] text-ink">{part.trim()}</p>
                ))}
              </div>
            </section>
          )}
        </div>
        {/* Under the sheet like a field's helper line, on the page's own
            ground (the danger red holds its contrast there, not on the
            sheet's): the count and, past the limit, what to do - two things
            on one line, so a gap between them (27/09) - and Clear. An empty
            sheet has neither: the hint under it says the limit. */}
        {!empty && (
          <div className="mb-8 mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 px-5 text-xs text-ink-mute">
            <span className={`tabular-nums ${overLimit ? "font-semibold text-danger" : ""}`}>{count}</span>
            {overLimit && <span className="font-medium text-danger">{text("paste.over_limit")}</span>}
            <Button variant="ghost" size="sm" onClick={onClear} className="-mr-2.5 ml-auto">{text("paste.clear")}</Button>
          </div>
        )}
        {empty && (
          /* The rows' hover wash reaches past the column; the scroller
             reaches out with them, or overflow-y makes them a sideways
             scroll (owner's screenshot, 21/10). */
          <div className="-mx-3 mt-3 min-h-0 flex-1 overflow-y-auto px-3 pb-4">
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
      </div>
    </section>
  );
}
