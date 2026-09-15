/** The reading models, one per language, each downloaded on request - this
 * is where somebody chooses which languages this Mac reads (owner, 15/09:
 * "user có thể lựa chọn model ngôn ngữ tuỳ theo nhu cầu", and the same
 * day: "không được bắt buộc user phải tải một model duy nhất nào đó").
 *
 * Rows only: what is installed and what is in flight live in `useModels`,
 * so the first-run screen, the hub and the settings panel's empty tab all
 * draw the same facts and any of them can start the download.
 *
 * The Vietnamese model has two builds; a switch restarts the engine process
 * (the build loads at construction), so the rows are loud about that,
 * download what is missing first (streaming the engine's own progress),
 * and only offer to delete the build that is NOT in use (the engine
 * refuses anything else anyway). The English model is one download, kept
 * or removed; its voices appear in the voice list only while it is here.
 */
import { text } from "../i18n";
import { Button, ProgressBar } from "./controls";
import { formatSize } from "./format";
import { GroupedRow, GroupedSection } from "./patterns";
import type { Language } from "./readingSources";
import type { Models } from "./useModels";

const BUILDS = [
  { id: "int8", label: () => text("model.build_standard") },
  { id: "fp32", label: () => text("model.build_maximum") },
] as const;

/** The rows for one language's model. */
export function ModelRows({
  language,
  models,
  reading,
  title,
}: {
  language: Language;
  models: Models;
  /** Nothing is fetched or removed under a running reading. */
  reading: boolean;
  /** The section heading, when the rows stand in a list of languages; none
   * when the language is already the whole panel. */
  title?: string;
}) {
  const { status, job } = models;
  const busy = job !== null || reading;
  if (language === "en") {
    const english = status?.english;
    if (!english) return null;
    return (
      <GroupedSection title={title}>
        <GroupedRow
          title={text("model.english_build")}
          subtitle={
            english.ready
              ? text("model.english_ready", { size: formatSize(english.installed) ?? "" })
              : english.installed > 0
                /* A cancelled download keeps the files that landed whole,
                   for the resume - up to the 326 MB model. Said as what it
                   is, with both ways out, rather than "not downloaded" over
                   a third of a gigabyte the row would not let go of. */
                ? text("model.english_partial", { size: formatSize(english.installed) ?? "" })
                : text("model.not_downloaded")
          }
          trailing={
            <>
              {!english.ready && (
                <Button
                  variant="primary"
                  size="sm"
                  disabled={busy}
                  onClick={() => void models.downloadEnglish()}
                >
                  {text(english.installed > 0 ? "model.english_resume" : "model.download")}
                </Button>
              )}
              {(english.ready || english.installed > 0) && (
                <Button size="sm" disabled={busy} onClick={() => void models.removeEnglish()}>
                  {text("model.english_remove")}
                </Button>
              )}
            </>
          }
        />
      </GroupedSection>
    );
  }
  return (
    <GroupedSection title={title}>
      {BUILDS.map((build) => {
        // "In use" is the build the engine is configured for - which, on a
        // Mac that never downloaded it, is a build that is not here yet.
        // That row offers the download rather than claiming to be in use.
        const chosen = status?.precision === build.id;
        const installed = (status?.installed[build.id] ?? 0) > 0;
        const active = chosen && installed && Boolean(status?.ready);
        return (
          <GroupedRow
            key={build.id}
            title={build.label()}
            subtitle={
              active
                ? text("model.in_use")
                : installed
                  ? undefined
                  : text("model.not_downloaded")
            }
            trailing={
              !active && (
                <>
                  {/* Three sentences for three states, because two of them
                      restart the engine and one does not: the configured
                      build that is not here yet is fetched in place; the
                      other build is switched to - fetched first if it must
                      be - and the switch is what the label says. */}
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={busy}
                    onClick={() => void models.downloadVietnamese(build.id)}
                  >
                    {text(chosen ? "model.download" : installed ? "model.use_build" : "model.download_use")}
                  </Button>
                  {installed && (
                    <Button
                      size="sm"
                      disabled={busy}
                      onClick={() => void models.removeVietnamese(build.id)}
                    >
                      {text("model.spare_remove")}
                    </Button>
                  )}
                </>
              )
            }
          />
        );
      })}
    </GroupedSection>
  );
}

/** The download in flight and the last word about one, under whichever
 * rows started it. */
export function ModelProgress({ models, className = "" }: { models: Models; className?: string }) {
  const { job, note } = models;
  if (!job && !note) return null;
  return (
    <div className={className}>
      {job && (
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <ProgressBar value={job.progress ?? 0} />
          </div>
          <Button size="sm" onClick={models.cancel}>
            {text("model.cancel")}
          </Button>
        </div>
      )}
      {(job?.message ?? note) && (
        <p className="m-0 mt-2 text-xs leading-relaxed text-ink-mute">{job?.message ?? note}</p>
      )}
    </div>
  );
}
