/** The place where the list of voices is decided.
 *
 * The engine offers twenty. Picking one out of twenty in the middle of a
 * chapter is not a thing anyone wants to do, so this panel is where the
 * choosing happens ONCE - listen, mark the ones worth keeping - and the
 * reading UI then offers only those (owner, 03/09).
 *
 * Preview is not offered while something is being read, and that is a fact
 * about the engine rather than a decision here: it speaks one thing at a
 * time, so a preview would cancel the reading it was meant to help you
 * change. The two halves are meant for different moments - listen here when
 * idle, switch from the footer when reading.
 */
import { useState } from "react";
import { text } from "../i18n";
import { Button, IconButton, Notice, SearchField, Surface, Switch } from "./controls";
import { Cluster, GroupedSection, useDismiss } from "./patterns";
import {
  CloseIcon, CloudIcon, ManIcon, MonitorIcon, SearchIcon, SpeakerIcon, StopIcon, WomanIcon,
} from "./icons";
import {
  matchesVoiceFilters,
  speaksVietnamese,
  tidyName,
  voiceDescription,
  voiceGender,
  type Voice,
  type VoiceGender,
} from "./voiceShortlist";
import { isPaidVoice, PROVIDERS, providerOf } from "./readingCost";

export function VoicesPanel({
  voices,
  error,
  shortlist,
  voiceId,
  reading,
  previewing,
  onToggle,
  onPreview,
  onStopPreview,
  onClose,
}: {
  voices: Voice[];
  /** Why the catalogue is empty, when it is empty because we could not ask. */
  error?: string | null;
  shortlist: string[];
  voiceId: string;
  /** Something is being read, so the engine cannot also speak a sample. */
  reading: boolean;
  /** The voice whose sample is playing right now, if any. */
  previewing: string | null;
  onToggle: (id: string) => void;
  onPreview: (id: string) => void;
  onStopPreview: () => void;
  onClose: () => void;
}) {
  const panel = useDismiss(onClose);
  const [query, setQuery] = useState("");
  // Folded away by default; the button in the header opens it.
  const [searching, setSearching] = useState(false);
  const [providerFilter, setProviderFilter] = useState("all");
  const [genderFilter, setGenderFilter] = useState<"all" | VoiceGender>("all");
  const sourceOf = (id: string) => providerOf(id) ?? "local";
  const providerOrder = ["local", ...PROVIDERS.map((provider) => provider.id)];
  const providerOptions = providerOrder.filter((key) =>
    voices.some((voice) => sourceOf(voice.id) === key));
  const activeProvider = providerFilter === "all" || providerOptions.includes(providerFilter)
    ? providerFilter
    : "all";
  const hasKnownGender = voices.some((voice) =>
    voiceGender(voice, sourceOf(voice.id) === "local") !== null);

  /* Grouped by where a voice comes FROM, because that is the question being
     answered here: the model on this Mac costs nothing and is always there;
     the others bill, and an ElevenLabs account can hold forty-five of them
     (owner, 05/09). One flat list of fifty-four with no way to search was
     not a list anyone could work with. */
  const matched = voices.filter((voice) => matchesVoiceFilters(
    voice,
    query,
    sourceOf(voice.id),
    activeProvider,
    genderFilter,
  ));
  const groups = providerOrder
    .map((key) => ({
      key,
      title: key === "local"
        ? text("voices.group_local")
        : PROVIDERS.find((provider) => provider.id === key)?.label ?? key,
      voices: matched
        .filter((voice) => sourceOf(voice.id) === key)
        // The ones the provider vouches for in Vietnamese come first: in
        // an account of forty-five English character voices, those are
        // the handful this reader is looking for. Alphabetical after.
        .sort((a, b) =>
          Number(speaksVietnamese(b)) - Number(speaksVietnamese(a))
          || tidyName(a.label).localeCompare(tidyName(b.label), "vi")),
    }))
    .filter((group) => group.voices.length > 0);
  const found = groups.reduce((total, group) => total + group.voices.length, 0);

  return (
    <Surface
      edge="strong"
      radius="sheet"
      ref={panel}
      className="absolute bottom-[calc(var(--shell-bottom-inner)+var(--layer-gap))] right-6 z-30 flex layer-capped w-[32rem] max-w-[calc(100vw-3rem)] flex-col shadow-lifted"
    >
      <div className="flex items-start gap-3 px-6 pb-4 pt-5">
        <div className="min-w-0 flex-1">
          <h3 className="m-0 text-base font-bold">{text("voices.title")}</h3>
          <p className="m-0 mt-1 text-xs text-ink-mute">{text("voices.caption")}</p>
        </div>
        {/* Search is FOLDED AWAY behind its own button (owner, 06/09:
            "chúng ta không ưu tiên tìm kiếm bằng từ khóa lắm"). What the list
            is really used for is scanning and toggling, and a permanent field
            over it spent a row insisting otherwise. Closing it clears the
            query: a hidden field still filtering the list would be a list
            quietly missing voices with nothing on screen to say why. */}
        {voices.length > 8 && (
          <IconButton
            onClick={() => {
              setSearching((open: boolean) => {
                if (open) setQuery("");
                return !open;
              });
            }}
            aria-expanded={searching}
            aria-label={text("voices.search")}
            title={text("voices.search")}
            className={searching ? "text-ink" : ""}
          >
            <SearchIcon />
          </IconButton>
        )}
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>

      {voices.length > 8 && searching && (
        <div className="px-6 pb-3">
          <SearchField
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            label={text("voices.search")}
            onEscape={() => { setQuery(""); setSearching(false); }}
          />
        </div>
      )}

      {(providerOptions.length > 1 || hasKnownGender) && (
        <div className="px-6 pb-4">
          {/* Every filter on ONE wrapping row of chips, no captions over
              them, and a glyph on each except the two "all"s (owner, 06/09).
              Gender was a `Select`; as chips both dimensions are one kind of
              control, so the row reads as one thing you tune rather than a
              row plus a dropdown.
              SIBLINGS, not nested groups: nested, a group claims a whole
              line as one item and pushes the rest down even when there is
              room beside it. Flat, the row wraps where it actually runs out.
              "All" carries no glyph because it is the ABSENCE of a filter -
              there is nothing for a picture to be of - and the two of them
              keep their full names for a screen reader, since "Tất cả" alone
              does not say all of what. */}
          <Cluster className="flex-wrap">
              {providerOptions.length > 1 &&
                ["all", ...providerOptions].map((key) => {
                  const active = activeProvider === key;
                  const label = key === "all"
                    ? text("voices.filter_all")
                    : key === "local"
                      ? text("voices.group_local")
                      : PROVIDERS.find((provider) => provider.id === key)?.label ?? key;
                  return (
                    <Button
                      key={key}
                      size="sm"
                      variant={active ? "primary" : "secondary"}
                      aria-pressed={active}
                      aria-label={key === "all" ? text("voices.filter_all_providers") : undefined}
                      onClick={() => setProviderFilter(key)}
                    >
                      {key === "all"
                        ? null
                        : key === "local" ? <MonitorIcon /> : <CloudIcon />}
                      {label}
                    </Button>
                  );
                })}
              {hasKnownGender &&
                ([
                  ["all", text("voices.gender_all"), null],
                  ["male", text("voices.gender_male"), <ManIcon key="m" />],
                  ["female", text("voices.gender_female"), <WomanIcon key="w" />],
                ] as const).map(([key, label, glyph]) => {
                  const active = genderFilter === key;
                  return (
                    <Button
                      key={key}
                      size="sm"
                      variant={active ? "primary" : "secondary"}
                      aria-pressed={active}
                      onClick={() => setGenderFilter(key as "all" | VoiceGender)}
                    >
                      {glyph}
                      {label}
                    </Button>
                  );
                })}
          </Cluster>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto px-6">
        {found === 0 && (
          <Notice className="mb-4 block">
            {query.trim()
              ? text("voices.no_match", { query })
              : text("voices.no_filter_match")}
          </Notice>
        )}
        {groups.map((group) => (
        <GroupedSection key={group.key} title={`${group.title} (${group.voices.length})`}>
          {group.voices.map((voice) => {
            const inList = shortlist.includes(voice.id);
            const playing = previewing === voice.id;
            return (
              <div key={voice.id} className="flex items-center gap-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2 text-sm font-medium">
                    {tidyName(voice.label) || voice.id}
                    {/* Which of these cost money, said where they are CHOSEN.
                        This panel listed a paid OpenAI voice and the model on
                        this Mac in the same weight with nothing between them,
                        so the first a reader knew was the figure appearing in
                        the read button afterwards. The amount stays in that
                        button - it depends on what is about to be read, and
                        only the engine knows it - but which ones bill at all,
                        and who bills, belongs here (owner, 04/09). */}
                    {isPaidVoice(voice.id) && (
                      <span className="rounded-full bg-band px-2 py-0.5 text-xs font-normal text-ink-mute">
                        {/* "Trả phí" alone: the engine already builds these
                            labels as "Alloy · OpenAI", so naming the provider
                            again put OpenAI twice on one line. */}
                        {text("voices.paid")}
                      </span>
                    )}
                    {/* Same chip as "Trả phí", because it is the same kind of
                        fact: something true of the voice before you pick it.
                        Only shown when the provider verified it - absence
                        means nobody checked, not that it cannot. */}
                    {speaksVietnamese(voice) && (
                      <span className="rounded-full bg-band px-2 py-0.5 text-xs font-normal text-ink-mute">
                        {text("voices.speaks_vi")}
                      </span>
                    )}
                    {voice.id === voiceId && (
                      <span className="text-xs font-normal text-ink-faint">{text("voices.in_use")}</span>
                    )}
                  </div>
                  <div className="mt-0.5 text-xs text-ink-mute">{voiceDescription(voice.label)}</div>
                </div>
                <IconButton
                  onClick={() => (playing ? onStopPreview() : onPreview(voice.id))}
                  disabled={reading}
                  aria-label={text(playing ? "voices.stop_preview" : "voices.preview")}
                  title={text(reading ? "voices.preview_while_reading" : playing ? "voices.stop_preview" : "voices.preview")}
                  className={playing ? "text-brand-600" : ""}
                >
                  {playing ? <StopIcon /> : <SpeakerIcon />}
                </IconButton>
                <Switch
                  checked={inList}
                  onChange={() => onToggle(voice.id)}
                  label={text("voices.in_switcher", { name: tidyName(voice.label) || voice.id })}
                />
              </div>
            );
          })}
        </GroupedSection>
        ))}
      </div>

      <div className="border-t border-edge px-6 py-4">
        <Notice tone={error ? "error" : "ok"}>
          {error
            ? `${text("voices.unavailable")} (${error})`
            : reading
              ? text("voices.preview_while_reading")
              : text("voices.marked", { count: shortlist.length })}
        </Notice>
      </div>
    </Surface>
  );
}
