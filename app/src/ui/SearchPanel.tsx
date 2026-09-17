/** Search in the open book, beside the page (owner, 06/09: "học hỏi theo
 * Apple Books").
 *
 * One tab of the side column, beside the contents and the notes: the field
 * stays put and only the results scroll. Typing searches as you go; a result
 * is a line of the book with the words marked, under the chapter it is in;
 * choosing one shows that place and the column stays, so the next result is
 * one click away - the way Books does it.
 */
import { useMemo, useState } from "react";
import { text } from "../i18n";
import { Input } from "./controls";
import { ListRow } from "./patterns";
import { MAX_HITS, MIN_QUERY, foldQuery, searchBook, type SearchChapter, type SearchHit } from "./textSearch";

export function SearchPanel({
  chapters,
  onJump,
}: {
  chapters: readonly SearchChapter[];
  onJump: (hit: SearchHit) => void;
}) {
  const [query, setQuery] = useState("");
  const [chosen, setChosen] = useState<number | null>(null);
  const hits = useMemo(() => searchBook(chapters, query), [chapters, query]);
  const enough = foldQuery(query).length >= MIN_QUERY;

  const pick = (index: number) => {
    const hit = hits[index];
    if (!hit) return;
    setChosen(index);
    onJump(hit);
  };

  /* The Tìm tab of the side column (HIG 3.16): the field stays put at the
     top, only the hits scroll. The column stays open after a hit, so the
     next one is one click away - the way Books does it. */
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 px-4 pb-4">
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
      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-6">
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
    </div>
  );
}
