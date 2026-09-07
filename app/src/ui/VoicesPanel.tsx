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
import {
  Button, IconButton, Notice, SearchField, SegmentedControl, Surface, Switch,
} from "./controls";
import { Cluster, GroupedSection, useDismiss } from "./patterns";
import {
  CloseIcon, CloudIcon, ManIcon, MonitorIcon, SearchIcon, SlidersIcon, SpeakerIcon,
  StopIcon, WomanIcon,
} from "./icons";
import { useShortWindow } from "./useShortWindow";
import {
  canSpeak,
  matchesVoiceFilters,
  speaksVietnamese,
  vouchedFor,
  tidyName,
  voiceDescription,
  voiceGender,
  type Voice,
  type VoiceGender,
} from "./voiceShortlist";
import { isPaidVoice, PROVIDERS, providerOf } from "./readingCost";

/** One fact about a voice, as a glyph.
 *
 * These were word chips ("Trả phí", "Tiếng Việt") and the owner asked for
 * pictures instead (07/09). A glyph carries no meaning by itself, so it says
 * the same words twice over: to a pointer through `title`, and to the
 * accessibility tree through `role="img"` plus `aria-label` - which is what
 * keeps the row readable to somebody who never sees the emoji at all.
 *
 * No pill behind it. The pill existed to make WORDS read as a tag; an emoji
 * is already its own object, and a grey capsule around a flag only fights
 * the colour that makes it legible.
 */
function VoiceMark({ glyph, name }: { glyph: string; name: string }) {
  return (
    <span role="img" aria-label={name} title={name} className="text-sm leading-none">
      {glyph}
    </span>
  );
}

export function VoicesPanel({
  voices,
  error,
  shortlist,
  voiceId,
  reading,
  previewing,
  bookLanguage,
  detectedLanguage,
  onSetLanguage,
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
  /** The language the open book is read in, or null when no book is open -
   * a pasted passage is judged by its own words every time it is read, so
   * there is nothing here to set. */
  bookLanguage?: string | null;
  /** What the book's own words read as, whatever was decided. The panel
   * needs only this and `bookLanguage`: where they agree there is nothing to
   * say, and where they differ there is a suggestion to offer. Whether the
   * difference came from a reader's decision is the engine's business - the
   * decision is stored and stands, and the book is not read again on the
   * next launch. */
  detectedLanguage?: string | null;
  /** `null` withdraws the decision and lets the text speak for itself. */
  onSetLanguage?: (language: string | null) => void;
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
  // On a short window the filter chips are folded away behind their own
  // button, the way search already is. They are CONTROLS, so they are never
  // simply dropped - but a permanent 80px row of them on a panel that has
  // 239px in total leaves the list nothing, and a list of no voices is not a
  // thing filters can help with (measured 07/09).
  const short = useShortWindow();
  const [filtering, setFiltering] = useState(false);
  const sourceOf = (id: string) => providerOf(id) ?? "local";
  // A book's language decides which voices may be offered AT ALL, so it
  // narrows the list before anything the reader filters. Scrolling past
  // twenty Vietnamese voices the engine will refuse, to reach the one that
  // can read this English chapter, is a list working against its reader.
  const speakableVoices = bookLanguage
    ? voices.filter((voice) => canSpeak(voice, bookLanguage))
    : voices;
  const hiddenByLanguage = voices.length - speakableVoices.length;
  const providerOrder = ["local", ...PROVIDERS.map((provider) => provider.id)];
  const providerOptions = providerOrder.filter((key) =>
    speakableVoices.some((voice) => sourceOf(voice.id) === key));
  const activeProvider = providerFilter === "all" || providerOptions.includes(providerFilter)
    ? providerFilter
    : "all";
  const hasKnownGender = speakableVoices.some((voice) =>
    voiceGender(voice, sourceOf(voice.id) === "local") !== null);
  const hasFilters = providerOptions.length > 1 || hasKnownGender;
  const filtersShown = hasFilters && (!short || filtering);

  /* Grouped by where a voice comes FROM, because that is the question being
     answered here: the model on this Mac costs nothing and is always there;
     the others bill, and an ElevenLabs account can hold forty-five of them
     (owner, 05/09). One flat list of fifty-four with no way to search was
     not a list anyone could work with. */
  const matched = speakableVoices.filter((voice) => matchesVoiceFilters(
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
      /* `overflow-hidden` is not tidying: without it the rows above the
         list simply drew past the rounded surface when they came to more
         than the cap, and the footer ended up floating below the window edge
         with nothing behind it (owner's screenshot, 07/09). Clipped, the
         panel is at worst cut short at the bottom - which is what a panel
         with a cap should look like. */
      className="absolute bottom-[calc(var(--shell-bottom-inner)+var(--layer-gap))] right-6 z-30 flex layer-capped w-[32rem] max-w-[calc(100vw-3rem)] flex-col overflow-hidden shadow-lifted"
    >
      <div className="flex items-start gap-3 px-6 pb-4 pt-5">
        <div className="min-w-0 flex-1">
          <h3 className="m-0 text-base font-bold">{text("voices.title")}</h3>
          <p className="short-hidden m-0 mt-1 text-xs text-ink-mute">{text("voices.caption")}</p>
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
        {/* Rendered by the same boolean that folds the row, not by a CSS
            utility: `IconButton` already sets `display: flex`, and a
            `display: none` utility of equal weight does not reliably beat
            it. One mechanism, so the button and the row it opens can never
            disagree about what "short" means. */}
        {hasFilters && short && (
          <IconButton
            onClick={() => setFiltering((open: boolean) => !open)}
            aria-expanded={filtering}
            aria-label={text("voices.filters")}
            title={text("voices.filters")}
            className={filtering ? "text-ink" : ""}
          >
            <SlidersIcon />
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

      {/* The language of the BOOK, above the voices, because it decides
          which of them may speak at all: the model on this Mac is a
          Vietnamese one and the engine refuses to read anything else with
          it. A reader who lands here after being refused mid-chapter is
          exactly the person who needs this row, and it is the same row that
          undoes a wrong guess on a Vietnamese book whose diacritics were
          lost in a scan.

          Only when a book is open. A pasted passage is judged by its own
          words on every read, so there would be nothing to remember. */}
      {bookLanguage && onSetLanguage && (
        <div className="px-6 pb-4">
          <p className="m-0 mb-2 text-xs font-semibold text-ink-mute">
            {text("voices.language")}
          </p>
          {/* The suggestion is a DOT on the option itself, not a sentence
              underneath (owner, 07/09). Acting on it is tapping that option,
              which is the same tap it always was - so the nudge costs no row
              and adds no second way to do one thing. Shown only where there
              is something to suggest: the book's own words read as the other
              language. The dot has no meaning of its own, so it carries
              words for a pointer and for the accessibility tree. */}
          <SegmentedControl
            value={bookLanguage}
            label={text("voices.language")}
            options={(["vi", "en"] as const).map((code) => {
              const name = text(code === "vi" ? "voices.language_vi" : "voices.language_en");
              const suggested = detectedLanguage === code && detectedLanguage !== bookLanguage;
              return {
                value: code,
                label: suggested ? (
                  <>
                    <span
                      aria-hidden="true"
                      className="h-1.5 w-1.5 shrink-0 rounded-full bg-brand-600"
                    />
                    {name}
                  </>
                ) : (
                  name
                ),
                ariaLabel: suggested ? text("voices.language_suggested", { name }) : undefined,
                title: suggested ? text("voices.language_suggested", { name }) : undefined,
              };
            })}
            onChange={(chosen) => onSetLanguage(chosen)}
          />

        </div>
      )}

      {filtersShown && (
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
            {/* Order matters: the LANGUAGE is why a Vietnamese-only
                catalogue is empty for an English book, and saying "no voice
                matches your filters" there would send somebody to clear
                filters that were never the problem. */}
            {hiddenByLanguage > 0 && !query.trim()
              ? text("voices.none_for_language")
              : query.trim()
                ? text("voices.no_match", { query })
                : text("voices.no_filter_match")}
          </Notice>
        )}
        {found > 0 && hiddenByLanguage > 0 && (
          <p className="mb-1 mt-4 text-xs text-ink-mute">
            {text("voices.hidden_for_language", { count: hiddenByLanguage })}
          </p>
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
                        only the engine knows it - but which ones bill at all
                        belongs here (owner, 04/09).

                        A banknote rather than the words "Trả phí" (owner,
                        07/09), and nothing at all on a free voice: costing
                        nothing is the ordinary case, and a badge for the
                        ordinary case is twenty badges saying nothing. */}
                    {/* The marks sit in their own tighter group: they are
                        one cluster of facts about this voice, and spaced on
                        the row's own gap they read as three separate things
                        drifting away from the name. */}
                    <span className="flex items-center gap-1">
                      {isPaidVoice(voice.id) && (
                        <VoiceMark glyph="💵" name={text("voices.paid")} />
                      )}
                      {/* Same kind of fact, same kind of mark: something true
                          of the voice before you pick it. Only when the
                          provider verified it - absence means nobody checked,
                          never that it cannot. */}
                      {speaksVietnamese(voice) && (
                        <VoiceMark glyph="🇻🇳" name={text("voices.speaks_vi")} />
                      )}
                      {vouchedFor(voice, "en") && (
                        <VoiceMark glyph="🇬🇧" name={text("voices.speaks_en")} />
                      )}
                    </span>
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

      {/* A count of marked voices is a nicety; "the catalogue could not be
          fetched" and "the engine cannot preview while it is reading" are
          not. So the row stays for those two and stands down for the
          count. */}
      <div
        className={`border-t border-edge px-6 py-4 ${error || reading ? "" : "short-hidden"}`}
      >
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
