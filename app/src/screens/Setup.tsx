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
import { ReadingSources, type SourcesProps } from "../ui/SourcesHub";

export function FirstRun({ onEnter, ...sources }: SourcesProps & { onEnter: () => void }) {
  return (
    <div className="flex h-screen items-center justify-center px-6">
      {/* Centred while it fits, scrolling inside its own column when the
          window is short - the rows must never be cut off at the top. */}
      <div className="max-h-full w-[34rem] max-w-full overflow-y-auto py-10">
        <h1 className="m-0 text-center text-lg font-extrabold">{text("setup.title")}</h1>
        <p className="m-0 mt-2 text-center text-sm text-ink-mute">{text("setup.description")}</p>
        <ReadingSources {...sources} />
        <div className="mt-8 flex justify-center">
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
  );
}
