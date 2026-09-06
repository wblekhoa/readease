/** Search in the open book, beside the page (owner, 06/09: "học hỏi theo
 * Apple Books").
 *
 * Built like the contents panel, its sibling over the same page: a heading
 * that stays put, a way out, and only the results scrolling. Typing searches
 * as you go; a result is a line of the book with the words marked, under the
 * chapter it is in; choosing one shows that place. The panel stays open so
 * the next result is one click away - the way Books does it - and closes on
 * Escape, the ✕, or a click on the page.
 */
import { useMemo, useState } from "react";
import { text } from "../i18n";
import { IconButton, Input, Surface } from "./controls";
import { CloseIcon } from "./icons";
import { ListRow, useDismiss } from "./patterns";
import { MAX_HITS, MIN_QUERY, foldQuery, searchBook, type SearchChapter, type SearchHit } from "./textSearch";

export function SearchPanel({
  chapters,
  paged,
  onClose,
  onJump,
}: {
  chapters: readonly SearchChapter[];
  paged: boolean;
  onClose: () => void;
  onJump: (hit: SearchHit) => void;
}) {
  const [query, setQuery] = useState("");
  const [chosen, setChosen] = useState<number | null>(null);
  const hits = useMemo(() => searchBook(chapters, query), [chapters, query]);
  const enough = foldQuery(query).length >= MIN_QUERY;
  const panel = useDismiss(onClose);

  const pick = (index: number) => {
    const hit = hits[index];
    if (!hit) return;
    setChosen(index);
    onJump(hit);
  };

  return (
    <Surface
      ref={panel}
      edge="strong"
      /* A panel over the page: the sheet's radius, and content set in by 24
         (HIG 3.9d). A list of rows reaches that 24 through the row's own
         inset, so its track is narrower by exactly that much. */
      radius="sheet"
      className={`flex flex-col overflow-hidden absolute right-0 z-10 w-[22rem] shadow-lifted ${
        paged
          ? "top-0 max-h-full"
          : "top-[calc(var(--shell-top-inner)+var(--layer-gap))] layer-capped"
      }`}
    >
      <div className="flex shrink-0 items-center gap-2 px-6 pb-2 pt-5">
        <h3 className="m-0 flex-1 text-sm font-bold">{text("reader.search")}</h3>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>
      <div className="shrink-0 px-6 pb-3">
        <Input
          autoFocus
          type="search"
          value={query}
          placeholder={text("reader.search_placeholder")}
          aria-label={text("reader.search")}
          onChange={(event) => { setQuery(event.target.value); setChosen(null); }}
          onKeyDown={(event) => {
            if (event.key === "Enter") pick(chosen === null ? 0 : Math.min(hits.length - 1, chosen + 1));
          }}
          className="w-full"
        />
        <p className="m-0 mt-1.5 text-xs text-ink-mute">
          {!enough
            ? text("reader.search_hint")
            : hits.length === 0
              ? text("reader.search_none")
              : hits.length >= MAX_HITS
                ? text("reader.search_capped", { n: MAX_HITS })
                : text("reader.search_count", { n: hits.length })}
        </p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-3.5 pb-4">
        {hits.map((hit, index) => (
          <ListRow
            key={`${hit.segmentId}:${index}`}
            dense
            active={index === chosen}
            onPress={() => pick(index)}
            title={
              <span className="line-clamp-2 text-sm">
                {hit.before}
                <span className="rounded-sm bg-band px-0.5 font-semibold text-ink">{hit.match}</span>
                {hit.after}
              </span>
            }
            subtitle={<span className="text-xs text-ink-mute">{hit.chapterTitle}</span>}
          />
        ))}
      </div>
    </Surface>
  );
}
