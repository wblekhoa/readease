/** Move Apple Books notes between two copies of a book.
 *
 * The engine owns every dangerous step (plan again, back up, atomic copy);
 * this screen owns the one decision a person must make - which two books,
 * and whether the promised count is worth writing. The confirm card repeats
 * the number the engine will actually write, never a cached one.
 */
import { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { text, type TextKey } from "../i18n";
import { Button, IconButton, Notice, SectionTitle, Surface } from "../ui/controls";
import { BookChoice, EmptyState, GroupedSection } from "../ui/patterns";
import { ArrowLeftIcon } from "../ui/icons";
import { TransferIcon } from "../ui/icons";

type NotesBook = {
  asset_id: string;
  title: string;
  edition_id: string;
  progress: number;
};
type PlanItem = {
  kind: number;
  has_note: boolean;
  excerpt: string;
  verdict: string;
};
type Plan = {
  source_title: string;
  target_title: string;
  same_edition: boolean;
  copyable: number;
  items: PlanItem[];
  total: number;
};

function request<T>(method: string, params: object): Promise<T> {
  return invoke<{ result: T }>("engine_request", { method, params }).then(
    (reply) => reply.result,
  );
}

function errorText(raw: unknown): string {
  const message = String(raw);
  const token = message.replace(/^.*failed: /, "");
  const known = ["not_permitted", "ambiguous", "book_gone"];
  for (const name of known) {
    if (token.includes(name)) return text(`noteserr.${name}` as TextKey);
  }
  return message;
}

const VERDICT: Record<string, TextKey> = {
  "same-edition": "transfer.verdict_same",
  "needs-review": "transfer.verdict_review",
  "already-there": "transfer.verdict_already",
};

export function Transfer() {
  const [books, setBooks] = useState<NotesBook[] | null>(null);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    request<{ books: NotesBook[] }>("notes.books", {})
      .then((reply) => setBooks(reply.books))
      .catch((error) => {
        setBooks([]);
        setNotice(errorText(error));
      });
  }, []);

  const preview = useCallback(async () => {
    setNotice(null);
    setPlan(null);
    setConfirming(false);
    try {
      setPlan(await request<Plan>("notes.plan", { source, target }));
    } catch (error) {
      setNotice(errorText(error));
    }
  }, [source, target]);

  const transfer = useCallback(async () => {
    setBusy(true);
    setConfirming(false);
    setNotice(null);
    try {
      const result = await request<{
        outcome: string;
        written?: number;
        target_title?: string;
        count?: number;
        backup?: string;
      }>("notes.transfer", { source, target });
      const values: Record<string, string | number> = {
        count: result.written ?? result.count ?? 0,
        book: result.target_title ?? "",
        path: result.backup ?? "",
      };
      setNotice(text(`outcome.${result.outcome}` as TextKey, values));
      if (result.outcome === "copied") setPlan(null);
    } catch (error) {
      setNotice(errorText(error));
    } finally {
      setBusy(false);
    }
  }, [source, target]);

  /* How far this copy got is what tells three books of the same name apart,
     and it is the fact the choice actually turns on: notes move OUT of the
     one you have been reading. The old menu threw it away. */
  const choices = (books ?? []).map((book) => ({
    id: book.asset_id,
    title: book.title,
    note: book.progress > 0
      ? text("library.progress", { percent: Math.round(book.progress * 100) })
      : null,
  }));

  const ready = source && target && source !== target;

  /* Swapping used to mean re-picking both menus, having realised halfway
     that the notes were about to go the wrong way. The plan goes with it:
     a plan is a promise about a DIRECTION, and one kept across a swap would
     state the wrong number for the wrong book. */
  const swap = useCallback(() => {
    setSource(target);
    setTarget(source);
    setPlan(null);
    setConfirming(false);
    setNotice(null);
  }, [source, target]);

  const chooser = (
    <div className="grid w-full max-w-[46rem] grid-cols-[1fr_auto_1fr] gap-x-3">
      <BookChoice
        label={text("transfer.source")}
        value={source}
        placeholder={text("transfer.pick_book")}
        books={choices}
        onChange={setSource}
      />
      <div className="flex flex-col gap-1.5">
        {/* An invisible copy of the pickers' label line, so the arrow sits on
            the cards' own centre without anybody hardcoding a card height. */}
        <span className="text-xs uppercase" aria-hidden="true">
          &nbsp;
        </span>
        <div className="flex flex-1 items-center">
          <IconButton
            aria-label={text("transfer.swap")}
            title={text("transfer.swap")}
            disabled={!source && !target}
            onClick={swap}
          >
            <TransferIcon />
          </IconButton>
        </div>
      </div>
      <BookChoice
        label={text("transfer.target")}
        value={target}
        placeholder={text("transfer.pick_book")}
        books={choices}
        onChange={setTarget}
      />
    </div>
  );

  if (!plan) {
    /* No plan yet: choosing the two books IS the screen, so it stands in the
       middle rather than clinging to a corner of an empty sheet - the shape
       the empty shelf and the empty scan list already use (owner, 09/09).
       The moment a plan exists the list needs the room and this moves back up
       to be a header for it. */
    return (
      <section className="shell-inset flex min-h-0 flex-1 flex-col">
        {/* No icon: the two cards ARE the picture, and the same glyph is on
            the swap button between them. */}
        <EmptyState
          actions={
            /* The sheet is empty apart from this, so the choosing gets room
               to stand in rather than a tight stack (owner, 09/09). */
            <div className="flex w-full flex-col items-center gap-7">
              <div className="text-center">
                <SectionTitle>{text("transfer.title")}</SectionTitle>
                <p className="m-0 mt-0.5 text-sm text-ink-mute">
                  {text("transfer.description")}
                </p>
              </div>
              {chooser}
              <Button disabled={!ready} onClick={() => void preview()}>
                {text("transfer.preview")}
              </Button>
              {notice && (
                <Notice tone="error" className="max-w-[60ch] text-center">{notice}</Notice>
              )}
            </div>
          }
          note={!ready ? text("transfer.pick_two") : undefined}
        />
      </section>
    );
  }

  /* Which two books, said once - the plan's OWN record of them, not the
     pickers re-read. A plan is about a pair; showing a control that can
     change that pair while the plan is on screen invites a list that no
     longer describes what the button would do. */
  const facts = (title: string, assetId: string) => {
    const book = (books ?? []).find((entry) => entry.asset_id === assetId);
    return (
      /* Sized to the title, not to half the row: stretched, the arrow drifted
         out to the middle and stopped reading as "this one into that one".
         Long titles still give way - they truncate rather than push. */
      <span className="min-w-0 shrink">
        {/* The subject of the whole screen, so it leads the type scale: the
            count below it decides an action, but only once you know which
            two books it is about. */}
        <span className="block truncate text-base font-bold leading-6" title={title}>
          {title}
        </span>
        {book && book.progress > 0 && (
          <span className="block truncate text-xs text-ink-mute">
            {text("library.progress", { percent: Math.round(book.progress * 100) })}
          </span>
        )}
      </span>
    );
  };

  return (
    <section className="shell-inset flex min-h-0 flex-1 flex-col">
      {/* Nothing to choose here any more. The pair is settled, so the screen
          is the PREVIEW: the two books stated, the way back out, and the
          list. Changing books means going back to choosing them - the same
          shape a single scanned passage uses on the other screen (owner,
          10/09). */}
      <div className="flex items-start gap-3">
        <IconButton
          aria-label={text("transfer.change_books")}
          title={text("transfer.change_books")}
          onClick={() => {
            setPlan(null);
            setConfirming(false);
            setNotice(null);
          }}
        >
          <ArrowLeftIcon />
        </IconButton>
        {/* Top-aligned, not centred: one copy carries a progress line and the
            other may not, and centring each block against the other put the
            two titles on different lines (owner, 10/09). They share the
            first line; whatever hangs below it hangs. */}
        <div className="flex min-w-0 flex-1 items-start gap-2.5">
          {facts(plan.source_title, source)}
          <ArrowLeftIcon className="h-6 shrink-0 rotate-180 text-ink-faint" />
          {facts(plan.target_title, target)}
        </div>
      </div>
      {/* A callout, not a line in the type ladder. As plain text it competed
          with the count for the same rung; on its own ground it reads as
          what it is - a standing promise about what the button will do -
          without having to win a size contest to be noticed. */}
      <Notice tone="info" className="mt-3 max-w-[60ch]">
        {text("transfer.description")}
      </Notice>
      {notice && (
        <Notice tone="error" className="mt-3 max-w-[60ch]">{notice}</Notice>
      )}

      {plan && (
        <div className="mt-5 flex min-h-0 flex-1 flex-col">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold">
              {text("transfer.count", { count: plan.copyable })}
            </span>
            {/* Only `same-edition` is ever written (TransferPlan.copyable), so
                a list of four with a count of two left the reader to work out
                which two. `total` is the whole set even when the list is
                capped, so this number is exact either way. */}
            {plan.total > plan.copyable && (
              <span className="text-xs text-ink-mute">
                {text("transfer.left_out", { count: plan.total - plan.copyable })}
              </span>
            )}
            {plan.total > plan.items.length && (
              <span className="text-xs text-ink-mute">
                {text("transfer.truncated", { shown: plan.items.length })}
              </span>
            )}
            <div className="flex-1" />
            {plan.copyable > 0 && !confirming && (
              <Button variant="primary" disabled={busy} onClick={() => setConfirming(true)}>
                {text("transfer.copy")}
              </Button>
            )}
          </div>
          {confirming && (
            <Surface className="mt-3 max-w-[64ch] p-4">
              <p className="m-0 text-sm font-bold">{text("transfer.confirm_title")}</p>
              <p className="m-0 mt-1 text-sm leading-relaxed text-ink-mute">
                {text("transfer.confirm_body", {
                  count: plan.copyable,
                  book: plan.target_title,
                })}
              </p>
              <p className="m-0 mt-1 text-sm leading-relaxed text-ink-mute">
                {text("transfer.confirm_icloud")}
              </p>
              <div className="mt-3 flex gap-2">
                <Button variant="primary" disabled={busy} onClick={() => void transfer()}>
                  {text("transfer.copy")}
                </Button>
                <Button disabled={busy} className="px-3" onClick={() => setConfirming(false)}>
                  {text("transfer.keep")}
                </Button>
              </div>
            </Surface>
          )}
          <GroupedSection className="mt-2 min-h-0 flex-1 overflow-y-auto">
            {plan.items.map((item, index) => (
              /* Three verdicts, three different things to feel - and they
                 shared one alarm colour. "Already in the other copy" is
                 nothing to do, and it shouted exactly as loudly as a note
                 that will be LEFT BEHIND. Danger is for what went wrong; a
                 note that cannot carry over is a caveat, and one already
                 there is barely news. */
              <div
                key={index}
                className={`flex items-baseline gap-3 py-2.5 ${
                  item.verdict === "already-there" ? "opacity-60" : ""
                }`}
              >
                <span className="w-24 shrink-0 text-xs font-medium text-ink-mute">
                  {text(item.has_note ? "transfer.kind_note" : "transfer.kind_highlight")}
                </span>
                {/* A clipped excerpt owes its own words back on hover - the
                    rule the library's titles and fact lines follow. */}
                <span
                  className="min-w-0 flex-1 truncate text-sm"
                  title={item.excerpt || undefined}
                >
                  {item.excerpt || text("transfer.no_text")}
                </span>
                <span
                  className={
                    "shrink-0 text-xs font-medium " +
                    (item.verdict === "needs-review" ? "text-warn" : "text-ink-mute")
                  }
                >
                  {text(VERDICT[item.verdict] ?? "transfer.verdict_review")}
                </span>
              </div>
            ))}
          </GroupedSection>
        </div>
      )}
    </section>
  );
}
