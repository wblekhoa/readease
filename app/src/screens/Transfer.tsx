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
import { Button, Field, Notice, SectionTitle, Select, Surface } from "../ui/controls";
import { EmptyState, GroupedSection } from "../ui/patterns";
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

  const pickers = (["source", "target"] as const).map((role) => (
    <Field
      key={role}
      label={text(role === "source" ? "transfer.source" : "transfer.target")}
    >
      <Select
        className="min-w-0 max-w-64"
        value={role === "source" ? source : target}
        onChange={(event) =>
          role === "source"
            ? setSource(event.target.value)
            : setTarget(event.target.value)
        }
      >
        <option value="">{text("transfer.pick_book")}</option>
        {books?.map((book) => (
          <option key={book.asset_id} value={book.asset_id}>
            {book.title}
          </option>
        ))}
      </Select>
    </Field>
  ));

  const ready = source && target && source !== target;

  if (!plan) {
    /* No plan yet: choosing the two books IS the screen, so it stands in the
       middle rather than clinging to a corner of an empty sheet - the shape
       the empty shelf and the empty scan list already use (owner, 09/09).
       The moment a plan exists the list needs the room and this moves back up
       to be a header for it. */
    return (
      <section className="shell-inset flex min-h-0 flex-1 flex-col">
        <EmptyState
          icon={<TransferIcon className="h-8 w-8" />}
          actions={
            <div className="flex flex-col items-center gap-3">
              <div className="text-center">
                <SectionTitle>{text("transfer.title")}</SectionTitle>
                <p className="m-0 mt-0.5 text-sm text-ink-mute">
                  {text("transfer.description")}
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-4">
                {pickers}
                <Button disabled={!ready} onClick={() => void preview()}>
                  {text("transfer.preview")}
                </Button>
              </div>
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

  return (
    <section className="shell-inset flex min-h-0 flex-1 flex-col">
      <SectionTitle>{text("transfer.title")}</SectionTitle>
      <p className="m-0 mt-0.5 text-sm text-ink-mute">
        {text("transfer.description")}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-4">
        {pickers}
        <Button disabled={!ready} onClick={() => void preview()}>
          {text("transfer.preview")}
        </Button>
      </div>
      {notice && (
        <Notice tone="error" className="mt-3 max-w-[60ch]">{notice}</Notice>
      )}

      {plan && (
        <div className="mt-4 flex min-h-0 flex-1 flex-col">
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
