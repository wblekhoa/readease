import { useState } from "react";
import { text } from "../i18n";
import { Button, IconButton, Select, Surface } from "./controls";
import { CloseIcon } from "./icons";
import { useDismiss } from "./patterns";
import { chapterRange } from "./audiobook";
import { voiceName } from "./voiceShortlist";

export function BookExportPanel({ title, chapters, voice, rate, available, busy, onStart, onClose }: {
  title: string; chapters: number; voice: string; rate: number; available: boolean; busy: boolean;
  onStart: (range: { fromChapter: number; chapters: number }) => void; onClose: () => void;
}) {
  const layer = useDismiss(onClose);
  const [first, setFirst] = useState(1);
  const [last, setLast] = useState(chapters);
  const range = chapterRange(first, last, chapters);

  return (
    <Surface
      ref={layer}
      modal={false}
      dialog={text("audiobook.title")}
      edge="strong"
      material="glass"
      radius="sheet"
      layer="popover"
      className="absolute right-6 top-[calc(var(--shell-top-inner)+var(--layer-gap))] z-20 flex layer-capped w-[30rem] max-w-[calc(100vw-3rem)] flex-col overflow-hidden shadow-lifted"
    >
      <div className="flex shrink-0 items-start gap-4 px-6 pb-5 pt-6">
        <div className="min-w-0 flex-1">
          <h2 className="m-0 text-base font-bold">{text("audiobook.title")}</h2>
          <p className="m-0 mt-2 break-words text-sm leading-relaxed text-ink-mute">{title}</p>
        </div>
        <IconButton onClick={onClose} aria-label={text("aria.close")}><CloseIcon /></IconButton>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-x-hidden overflow-y-auto px-6 pb-6">
        <dl className="m-0 grid grid-cols-[minmax(0,1fr)_auto_auto] gap-x-6 gap-y-4">
          <div className="min-w-0">
            <dt className="text-xs text-ink-mute">{text("audiobook.voice")}</dt>
            <dd className="m-0 mt-1 break-words text-sm font-medium">{voiceName(voice)}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-mute">{text("audiobook.rate")}</dt>
            <dd className="m-0 mt-1 text-sm font-medium">{rate}×</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-mute">{text("audiobook.format")}</dt>
            <dd className="m-0 mt-1 text-sm font-medium">M4B</dd>
          </div>
        </dl>

        <fieldset className="m-0 min-w-0 border-0 p-0">
          <legend className="p-0 text-sm font-semibold">{text("audiobook.range")}</legend>
          <div className="mt-3 grid grid-cols-2 gap-4">
            <label className="flex min-w-0 flex-col gap-2 text-xs text-ink-mute">
              {text("audiobook.from")}
              <Select label={text("audiobook.from")} value={first} onChange={e => setFirst(Number(e.target.value))}>
                {Array.from({ length: chapters }, (_, i) => <option key={i} value={i + 1}>{i + 1}</option>)}
              </Select>
            </label>
            <label className="flex min-w-0 flex-col gap-2 text-xs text-ink-mute">
              {text("audiobook.to")}
              <Select label={text("audiobook.to")} value={last} onChange={e => setLast(Number(e.target.value))}>
                {Array.from({ length: chapters }, (_, i) => <option key={i} value={i + 1}>{i + 1}</option>)}
              </Select>
            </label>
          </div>
        </fieldset>

        <p className="m-0 text-xs leading-relaxed text-ink-mute">{text("audiobook.background")}</p>
        {!available && <p role="status" className="m-0 text-sm leading-relaxed text-ink-mute">{text("audiobook.local_only")}</p>}
        {!range && <p role="alert" className="m-0 text-sm leading-relaxed text-danger">{text("audiobook.range_error")}</p>}
      </div>

      <div className="flex shrink-0 justify-end border-t border-edge px-6 py-5">
        <Button variant="primary" disabled={!available || busy || !range} onClick={() => { if (range) onStart(range); }}>
          {text("audiobook.save")}
        </Button>
      </div>
    </Surface>
  );
}
