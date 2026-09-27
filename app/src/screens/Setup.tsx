/** First run: nothing on this Mac can read yet.
 *
 * The Qt shell's gate made the Vietnamese model the price of entry; the
 * owner's decision (15/09) is that nobody is made to download any one
 * model - the reader chooses what this Mac reads. So this is the hub's own
 * rows in a frame: either model, or a key, or nothing for now, and the
 * library is a click away whatever was chosen. It shows on each launch
 * only while nothing can read, and never again once something can.
 */
import { text } from "../i18n";
import { Button } from "../ui/controls";
import { ModelProgress } from "../ui/ModelPanel";
import { ReadingSources, type SourcesProps } from "../ui/SourcesHub";

export function FirstRun({ onEnter, ...sources }: SourcesProps & { onEnter: () => void }) {
  return (
    <div className="flex h-screen items-center justify-center bg-ground px-6">
      {/* Centred while it fits, scrolling inside its own column when the
          window is short - the rows must never be cut off at the top. */}
      <div className="max-h-full w-[34rem] max-w-full overflow-y-auto pt-10">
        <h1 className="m-0 text-center text-lg font-extrabold">{text("setup.title")}</h1>
        <p className="m-0 mt-2 text-center text-sm text-ink-mute">{text("setup.description")}</p>
        <ReadingSources {...sources} />
        {/* The download and the way in stay in view: at the window's floor
            the rows run past the bottom, and a download started up there put
            its progress and its Cancel below them, out of sight (27/09).
            Stuck to the column's foot, they sit after the rows when all of it
            fits and over them when it does not. */}
        {/* The column's bottom padding lives in here, on the opaque ground:
            as the column's own it sat below this block, and the rows showed
            through it when the column scrolled. */}
        {/* A hairline on top, as the sheets' footers have: stuck over the
            rows, the progress otherwise sat right under whichever group's
            heading was left showing - "TIẾNG ANH" over a Vietnamese download. */}
        <div className="sticky bottom-0 mt-4 border-t border-edge bg-ground pb-10 pt-4">
          <ModelProgress models={sources.models} />
          <div className="mt-6 flex justify-center">
            {/* Always open. A person who wants to look at the shelf first, or
                who will add a key later, is not held at the door - the read
                button and the settings panel say what is still missing. */}
            <Button
              variant="primary"
              disabled={sources.models.job !== null}
              className="h-[34px] px-6"
              onClick={onEnter}
            >
              {text("setup.enter")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
