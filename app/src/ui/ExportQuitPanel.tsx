import { text } from "../i18n";
import { Button, Surface } from "./controls";
import { Scrim, useDismiss } from "./patterns";

export function ExportQuitPanel({ onKeep, onQuit }: { onKeep: () => void; onQuit: () => void }) {
  const layer = useDismiss(onKeep);
  return <>
    <Scrim />
    <Surface ref={layer} dialog={text("audiobook.quit_title")} modal edge="strong" radius="sheet" layer="popover"
      className="absolute left-1/2 top-1/2 z-50 w-[26rem] max-w-[calc(100vw-3rem)] -translate-x-1/2 -translate-y-1/2 p-6 shadow-lifted">
      <h2 className="m-0 text-base font-bold">{text("audiobook.quit_title")}</h2>
      <p className="text-sm text-ink-mute">{text("audiobook.quit_body")}</p>
      <div className="flex flex-wrap gap-2">
        <Button onClick={onKeep}>{text("audiobook.keep")}</Button>
        <Button variant="danger" onClick={onQuit}>{text("audiobook.quit")}</Button>
      </div>
    </Surface>
  </>;
}
