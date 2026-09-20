/** Search in the open book, beside the page (owner, 06/09: "học hỏi theo
 * Apple Books").
 *
 * One tab of the side column, beside the contents and the notes: the field
 * stays put and only the results scroll. Typing searches as you go; a result
 * is a line of the book with the words marked, under the chapter it is in;
 * choosing one shows that place and the column stays, so the next result is
 * one click away - the way Books does it.
 */
import { useEffect, useMemo, useState } from "react";
import { text } from "../i18n";
import { SearchField } from "./controls";
import { GroupedSection, ListRow } from "./patterns";
import { MAX_HITS, MIN_QUERY, foldQuery, searchBook, type SearchChapter, type SearchHit } from "./textSearch";

/** What the page needs to mark the matches: the query as typed, and which
 * match was just chosen in the list - by its paragraph and its place among
 * that paragraph's matches, which is how the page counts them too. */
export type SearchMarks = {
  query: string;
  current: { segmentId: string; occurrence: number } | null;
};

export function SearchPanel({
  chapters,
  onJump,
  onMarks,
}: {
  chapters: readonly SearchChapter[];
  onJump: (hit: SearchHit) => void;
  /** Told whenever the query or the chosen hit changes, and told "nothing"
   * when the panel goes away - the page's marks live exactly as long as
   * the Tìm tab holds a query (HIG 3.16, owner 17/09). */
  onMarks?: (marks: SearchMarks) => void;
}) {
  const [query, setQuery] = useState("");
  const [chosen, setChosen] = useState<number | null>(null);
  const hits = useMemo(() => searchBook(chapters, query), [chapters, query]);
  const enough = foldQuery(query).length >= MIN_QUERY;
  /* Hits come in chapter order, so a chapter's hits are one run; each run
     is a group under the chapter's name, said once (HIG 3.16). */
  const groups = useMemo(() => {
    const out: { chapterId: string; chapterTitle: string; items: { hit: SearchHit; index: number }[] }[] = [];
    hits.forEach((hit, index) => {
      const last = out[out.length - 1];
      if (last && last.chapterId === hit.chapterId) last.items.push({ hit, index });
      else out.push({ chapterId: hit.chapterId, chapterTitle: hit.chapterTitle, items: [{ hit, index }] });
    });
    return out;
  }, [hits]);
  useEffect(() => {
    if (!onMarks) return;
    const hit = chosen === null ? undefined : hits[chosen];
    const current = hit
      ? {
        segmentId: hit.segmentId,
        occurrence: hits.slice(0, chosen!).filter((other) => other.segmentId === hit.segmentId).length,
      }
      : null;
    onMarks({ query: enough ? query : "", current });
  }, [onMarks, query, enough, hits, chosen]);
  useEffect(() => () => { onMarks?.({ query: "", current: null }); }, [onMarks]);

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
        {/* The search box that says it is one (controls.tsx::SearchField):
            36 tall with the lens inside, the same field the voices list
            searches with - the plain 30 px Input it replaced read as a row
            in a form (owner, 17/09: "input size lớn hơn xíu"). Escape clears
            the query here, before anything around the column sees it. */}
        <SearchField
          autoFocus
          material
          value={query}
          label={text("reader.search")}
          placeholder={text("reader.search_placeholder")}
          onChange={(event) => { setQuery(event.target.value); setChosen(null); }}
          onKeyDown={(event) => {
            if (event.key === "Enter") pick(chosen === null ? 0 : Math.min(hits.length - 1, chosen + 1));
            if (event.key === "Escape" && query) { event.stopPropagation(); setQuery(""); setChosen(null); }
          }}
          className="w-full"
        />
        <p className="m-0 mt-3 text-xs text-ink-mute">
          {!enough
            ? text("reader.search_hint")
            : hits.length === 0
              ? text("reader.search_none")
              : hits.length >= MAX_HITS
                ? text("reader.search_capped", { n: MAX_HITS })
                : text("reader.search_count", { n: hits.length })}
        </p>
      </div>
      {/* The track is narrower than the box above it by exactly the row's
          own inset (dense = 10 px), so a hit's TEXT starts where the search
          box and the tab pill start - 16 px in - and only the hover wash
          reaches out past it (HIG 3.9d; owner, 17/09: "align với các thành
          phần khác"). */}
      <div className="min-h-0 flex-1 overflow-y-auto px-1.5 pb-6">
        {/* A hit is for recognising the right match in a second: the match
            in the page's own yellow (the same mark the page draws, so one
            colour means one thing in both places), the words around it
            mute, and the chapter's name once over its run of hits rather
            than under every row (owner, 17/09). The group's header sits
            at the rows' text inset, 10 px in from the track. */}
        {groups.map((group) => (
          <GroupedSection
            key={group.chapterId}
            heading="name"
            title={group.chapterTitle}
            className="[--dot-inset:0.625rem] [&>h3]:px-2.5"
          >
            {group.items.map(({ hit, index }) => (
              <ListRow
                key={`${hit.segmentId}:${index}`}
                dense
                active={index === chosen}
                onPress={() => pick(index)}
                title={
                  <span className="line-clamp-2 py-0.5 text-sm text-ink-mute">
                    {hit.before}
                    <mark data-search={index === chosen ? "current" : "match"} className="font-semibold text-ink">{hit.match}</mark>
                    {hit.after}
                  </span>
                }
              />
            ))}
          </GroupedSection>
        ))}
      </div>
    </div>
  );
}
