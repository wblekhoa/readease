# Privacy

ReadEase is a local-first macOS reader. It does not run an HTTP server, send
telemetry, or upload document content to the ReadEase publisher. Out of the box it
needs no API key. Once a voice model is prepared, reading with it needs no
network; software-update checks and optional browser/provider connections are
described below.

An optional **outside AI voice** (see below) sends the passage being read to
the provider whose key you entered.
Nothing about it is on by default and nothing turns it on by itself.

Every source copy and app bundle carries the same static provenance marker,
`READEASE-THU-AM-NC-2026-01`, to identify the ReadEase scaffold and its license.
It is not generated from the user, Mac, installation, documents, or clipboard; it
never changes per copy and is not transmitted anywhere.

## Data kept on the Mac

Imported documents, normalized reading text, progress, preferences, downloaded
model files, and reusable document-audio cache live under
`~/Library/Application Support/VieNeu Reader/`. The historical folder name is
kept so existing readers do not lose their library when upgrading to ReadEase.

Pasted text and text read from a selection are never added to the library or
the persistent audio cache. By default ReadEase keeps a **history** of them on
this Mac - the text you read, and for a translated selection or paste its original and
translation - in `history.sqlite3` in the same folder, readable only by your
macOS user. No audio is kept, and none of it is sent anywhere. History keeps
entries for 30 days by default (7, 30, 90 or 365 days, or until you delete
them); older entries are deleted from the file. You can delete one entry,
everything, or switch history off in the History panel of the Paste and Read a
selection screens; switched off, nothing new is written. The Read
home can also show recent imported books derived from the library's existing
import/listening timestamps; those book records remain in the library.

## Optional translation before reading

“Translate before reading” is off by default. Apple Translation uses installed on-device language packs;
ReadEase does not download them or send the selected passage or pasted text to a translation website. It applies only to
the sources you switch on (Read a selection, Paste text). Apple may collect
framework usage/performance metadata under its system privacy policy, but not the original or translated text
([Apple TranslationSession documentation](https://developer.apple.com/documentation/Translation/TranslationSession)).

Alternatively, ReadEase sends the selected or pasted text to a local Ollama server on `127.0.0.1:11434` or LM Studio on
`127.0.0.1:1234`. These connections use no proxy, redirect, API key or remote endpoint. Ollama cloud models,
including aliases identified as remote by model metadata, are rejected. Install and run local models yourself;
ReadEase does not control a third-party server's own logging or configuration. Use locally hosted models only.

ReadEase can also download its own translator (Tencent's Hy-MT2, about 1.1 GB, from a pinned
Hugging Face revision checked against its published hash) when you ask for it in Voices & models.
It runs inside ReadEase's bundled translation server, which listens on 127.0.0.1 only and makes no
network connections of its own; the text never leaves this Mac. Remove it from the same place.

The original and its translation are kept in the History on this Mac described above, while History is on, and
nowhere else. Only translation preferences (provider, model name, source/target language, local voice, sources and
enabled state) are saved with your settings. Speaking the translation
uses an installed local voice, never an automatic fallback to a paid voice. Stop cancels an in-flight translation.

## Exported audio

Paste text can be exported as a WAV file with subtitles (`.srt`) beside it.
ReadEase writes only those two files, only where you choose them in the save
panel. So that a sentence can be said again before the file is saved anew, the
last export's audio is held, sentence by sentence, in a temporary file with no
name inside ReadEase; it is let go when you press Done in the review, change
the pasted text, start another export, or quit. Nothing else of the text or its
audio is kept anywhere, and nothing is
sent anywhere by the export itself (an API voice still sends the text to its
provider, exactly as when it reads aloud). The WAV's own metadata says that the
speech in it was made by a voice model, which voice, and with ReadEase. What
you do with an exported file, and where you publish it, is up to you.

An imported book, or a chapter range, can also be exported as a single M4B audiobook, with chapter titles and the
book's JPEG/PNG cover when available. This path accepts on-device voices only and sends nothing over the network.
It writes to the location you choose and does not change listening progress or add generated book audio to the cache.
Audio is staged on disk rather than held as one large in-memory buffer. Normalisation and encoding use temporary
WAV/AAC/M4B staging files in the chosen output folder; they are removed on completion, normal cancellation or failure.
The existing destination is replaced only after the new file is ready. A force quit or power loss can leave staging
files; it does not resume the export on relaunch. While ReadEase remains open, you can browse or minimise the window.
Completion/error requests Dock attention when unfocused; no book title or passage is sent to a notification service.

## Network use

Network access is used when the user explicitly prepares the local VieNeu
model. The backbone and codec are downloaded from the public model repositories
at the exact revisions listed in `legal/MODEL_PROVENANCE.md`. Once both are
verified locally, speech initialization fails closed on any remote lookup.

The optional English voice is the same kind of download, made only when you
press **Download** under Voices & models: the Kokoro model from
its public repository on huggingface.co, and two pronunciation lexicon files
from the misaki repository on GitHub (raw.githubusercontent.com), at the
revisions and hashes listed in `legal/MODEL_PROVENANCE.md`. Nothing about
your documents or your Mac is sent with either request. Reading English with
that voice afterwards is entirely local.

Optional outside AI voices send the passage to their selected provider, as
described below. Optional selection translation contacts only the installed
Apple framework or the loopback model servers described above.

The app also checks its published GitHub updater feed after startup and can
download a signed release archive. The feed address does not include document
text, book titles or API keys. Like ordinary HTTPS requests, this exposes request
metadata to the hosting service. The new background-update flow separates
download from explicit installation/restart; temporary reading text is not
snapshotted for restart.

**Help › Report a Problem or Suggest…** opens GitHub's issue form in your browser with three facts already filled
into the address - the app's build, the macOS version and the chip family
(Apple silicon or Intel). Nothing from your documents, library or settings
is added. Opening the prefilled URL sends those metadata fields to GitHub in
the browser request. It does not create an issue; the report is created only
after you review and submit the form yourself. Local diagnostic logs are not
automatically uploaded or attached.

## The website

The landing page (wblekhoa.github.io/readease) counts visits with Google
Analytics 4: page views and a few clicks (download, GitHub, language
switch, a voice demo started, a question opened). Google signals and ad
personalisation are off, and nothing loads when your browser sends Do Not
Track. This is the website only; the app sends nothing of the kind.

## Outside AI voices (off unless you turn them on)

ReadEase can read with a paid voice from OpenAI or ElevenLabs, on **your own
account and your own key**. This is the one place where the text you are
reading leaves this Mac, so it is worth being exact about what does and does
not happen.

**What is sent.** The passage about to be spoken, sentence by sentence as the
reading advances, and the identifier of the voice. Nothing else: not the document,
not its title or file, not your progress, not your notes or highlights, not
your name, and nothing identifying this Mac or this installation. Text outside
the scope you chose is never sent at all — the scope is a ceiling, checked
before anything goes out, not a preference applied afterwards.

**Who it goes to.** Directly from your Mac to the provider you configured,
over HTTPS, on your key. It does not pass through any ReadEase server; there
is no ReadEase server. ElevenLabs requests are sent with `enable_logging=false`,
which asks them not to retain the text for review; what each provider does
with a request is governed by their terms and their retention policy, not by
this app.

**What it costs, and what you are told first.** These voices bill by the
character. ReadEase counts the exact characters it is about to send and shows
the figure in the read button before the reading starts; the button will not
start one until it can quote it. You can cap both how much of a document one press
may read and how much a session may spend.

**Your key.** It is written to `~/Library/Application Support/VieNeu Reader/
settings.json` with owner-only permissions (0600) and is write-only across the
app's internal pipe: the interface can ask whether a key is set and never what
it is, so no rendering bug can put it on screen. It is sent to that provider
and to nobody else, and it is never written to a log or an error message —
messages coming back from a provider are redacted before they are shown.

**If you never turn this on**, none of the above happens, and ReadEase behaves
exactly as it did before the feature existed: the voice runs on this Mac, and
after the first model download it needs no network.

## Apple Books library

The **Move notes** tab reads Apple Books' own databases so it can show which of your
notes and highlights could carry over between two copies of a document. It reads the list
of items and, for the two copies you pick, the annotations on them: their positions, the
text you highlighted, and the notes you wrote. Both copies are read because the preview
says which notes are already on the other side; they come out of one read, and no other
document in your library is read at all.

Nothing is read until you open that tab. Previewing never opens the originals for
writing: ReadEase copies the database files, reads the copy, and deletes it.

Previewing also opens the two files themselves. A note's position is recorded as
a count of elements inside one chapter, so it only means the same thing in the other
copy when that chapter is the same document — two files can share an edition id and
still differ inside. ReadEase reads each copy's package listing to learn its chapter
order, then takes a checksum of each chapter to compare the two. Chapter text is
hashed, never stored, never shown, and never leaves this Mac; only the two copies you
picked are opened.

**Copy across** does write to Apple Books, and it is the only thing in ReadEase that
writes to data belonging to another app. Apple does not support this, so it is built
to be undone:

- It only runs when you press the button, after a preview of that exact pair of copies,
  and after a confirmation naming the document and the number of items.
- It refuses while Apple Books is running, because Apple Books would overwrite the
  change.
- It copies the annotation database and its journal files into
  `~/Library/Application Support/VieNeu Reader/AppleBooksBackups/` before writing anything.
  The five most recent are kept and older ones are removed after a successful copy, so
  snapshots of your annotations do not pile up there indefinitely. Deleting that folder
  yourself is safe; it only costs the ability to go back.
- It only copies notes whose chapter is byte-for-byte the same document in both copies.
  Anything else stays listed, marked, and unwritten - copying it would put a highlight
  on the wrong words.
- It only ever inserts. The copy the notes came from is not modified, and nothing is
  deleted or edited in either copy. The files themselves are never written to at all.
- It skips anything already there, so pressing it again copies nothing rather than
  making a second set. A note already at that position in the target copy is left as
  it is, including one you wrote yourself.
- The whole copy is one transaction, so if it fails part way through, your library is
  left exactly as it was.

If Apple Books syncs with iCloud, notes copied this way sync to your other devices like
any other annotation. The confirmation says so before you agree.

That also bounds what the backup can undo. Restoring it puts this Mac's database back,
which is a clean undo only while Apple Books has not launched and synced since the
copy. Once it has, the copied notes exist in iCloud too and Apple Books will bring them
back; from that point the way to remove them is to delete them inside Apple Books,
where they are easy to find - they are the newest annotations on the copy you copied
into, and nothing else in that copy was touched.

What it reads stays on this Mac and is not stored by ReadEase: the table is built when
you press Preview and is gone when you close the app. macOS may ask you to grant
ReadEase access to that folder; if you decline, the tab says so and nothing else
changes.

## Clipboard and Accessibility

For the read-selection shortcut, ReadEase uses macOS Accessibility permission
to send Copy to whichever app is in front, so a selection can be read from a web
page, a PDF, an email or anywhere else - not only from Apple Books. It acts only
at the moment the shortcut is pressed: during that one action it snapshots the
current clipboard in memory, reads the selected text, and restores every
captured clipboard item. If restore cannot be confirmed, ReadEase does not read
the selection. Clipboard managers or Universal Clipboard may still observe this
brief copy transaction.

Because the shortcut reaches into any app, two limits are worth stating plainly.
A selection that its own app marks concealed - what password managers do - is
refused and never read. Everything else is read as-is, so what gets spoken is
whatever was selected when the shortcut was pressed; ReadEase cannot tell
sensitive text from ordinary text. Reading from ReadEase itself is refused.

The shortcut itself can be changed in the Read a selection view. The chosen key and
modifiers are stored in `settings.json`, beside the other preferences kept there
- the pronunciations you write (a word and how it should be said), which stay
  on this Mac like every other setting;
- the interface language, the voice and reading speed the app starts with, and
  which build of the reading model it uses;
nothing about your keyboard is recorded anywhere else.

ReadEase never watches the clipboard on its own. It reads only at the moment
you press the shortcut, and only what you had selected then; text read that way
is transient like the rest, is not added to the library or the persistent audio
cache, and never leaves this Mac.

Deleting ReadEase does not automatically delete its Application Support data.
Users can remove that folder separately after closing the app if they no longer
need their library, models, progress, or cache.
