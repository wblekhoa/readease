/** First run: the voice is not on this Mac yet.
 *
 * The whole app waits behind this one screen - the same gate the Qt shell
 * had - because every feature is a way of listening. One column, the form
 * fields on a shared axis, the single primary action in brand.
 */
import { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { text } from "../i18n";
import { Button, Field, ProgressBar, Select } from "../ui/controls";

export function Setup({
  precision,
  onReady,
}: {
  precision: string | null;
  onReady: () => void;
}) {
  const [choice, setChoice] = useState(precision ?? "int8");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [note, setNote] = useState<string>(text("setup.ready"));

  useEffect(() => {
    const progressEvents = listen<{ progress: number; message: string }>(
      "engine:model_progress",
      (event) => {
        setProgress(event.payload.progress);
        setNote(event.payload.message);
      },
    );
    const finished = listen<{ ok: boolean; error?: string }>(
      "engine:orphan_reply",
      (event) => {
        if (event.payload.ok) {
          onReady();
        } else {
          setBusy(false);
          setProgress(null);
          setNote(event.payload.error ?? text("setup.ready"));
        }
      },
    );
    return () => {
      progressEvents.then((unlisten) => unlisten());
      finished.then((unlisten) => unlisten());
    };
  }, [onReady]);

  const prepare = useCallback(async () => {
    setBusy(true);
    try {
      if (choice !== precision) {
        await invoke("engine_request", {
          method: "model.set_precision",
          params: { precision: choice },
        });
        await invoke("restart_engine");
      }
      await invoke("prepare_model");
    } catch (error) {
      setBusy(false);
      setNote(String(error));
    }
  }, [choice, precision]);

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="w-[420px]">
        <h1 className="m-0 text-center text-lg font-extrabold">
          {text("setup.title")}
        </h1>
        <p className="m-0 mt-1 text-center text-sm text-ink-mute">
          {text("setup.description")}
        </p>
        <Field label={text("setup.quality")} className="mt-6 justify-center gap-3">
          <Select
            disabled={busy}
            value={choice}
            onChange={(event) => setChoice(event.target.value)}
          >
            <option value="int8">{text("model.build_standard")}</option>
            <option value="fp32">{text("model.build_maximum")}</option>
          </Select>
        </Field>
        {progress !== null && (
          <div className="mt-5">
            <ProgressBar value={progress} />
          </div>
        )}
        <p className="m-0 mt-3 text-center text-sm text-ink-mute">{note}</p>
        <div className="mt-4 flex justify-center">
          <Button
            variant="primary"
            disabled={busy}
            className="h-[34px] px-6"
            onClick={() => void prepare()}
          >
            {text("setup.prepare")}
          </Button>
        </div>
      </div>
    </div>
  );
}
