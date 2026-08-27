# Privacy

ReadEase is a local-first macOS reader. It does not require an API key, run an
HTTP server, send telemetry, or upload book content to the ReadEase publisher.

Every source copy and app bundle carries the same static provenance marker,
`READEASE-THU-AM-NC-2026-01`, to identify the ReadEase scaffold and its license.
It is not generated from the user, Mac, installation, books, or clipboard; it
never changes per copy and is not transmitted anywhere.

## Data kept on the Mac

Imported books, normalized reading text, progress, preferences, downloaded
model files, and reusable book-audio cache live under
`~/Library/Application Support/VieNeu Reader/`. The historical folder name is
kept so existing readers do not lose their library when upgrading to ReadEase.

Pasted text and text selected in Apple Books are transient. They are not added
to the library or persistent audio cache. The recent-reading list is held in
memory and disappears when ReadEase exits.

## Network use

Network access is used only when the user explicitly prepares the local VieNeu
model. The backbone and codec are downloaded from the public model repositories
at the exact revisions listed in `legal/MODEL_PROVENANCE.md`. Once both are
verified locally, speech initialization fails closed on any remote lookup.

## Clipboard and Accessibility

For the Apple Books shortcut, ReadEase uses macOS Accessibility permission to
send Copy. During that one action it snapshots the current clipboard in memory,
reads the selected text, and restores every captured clipboard item. If restore
cannot be confirmed, ReadEase does not read the selection. Clipboard managers
or Universal Clipboard may still observe this brief copy transaction.

The shortcut itself can be changed in the Read books view. The chosen key and
modifiers are stored in `settings.json` beside the language preference; nothing
about your keyboard is recorded anywhere else.

### Read on copy

"Read as soon as you copy in Apple Books" is off until you switch it on in the
Read books view, and it is the only setting that makes ReadEase look at the
clipboard on its own. While it is on, ReadEase checks the clipboard's change
counter a few times a second; when that counter moves and Apple Books is the
frontmost app, ReadEase reads the newly copied text aloud. In this mode it only
reads the clipboard, never writes to it, and it needs no Accessibility
permission.

The Apple Books check happens before any text is taken out of the clipboard, so
text you copy in another app - a password manager, a bank page, a chat window -
is never handed to ReadEase. That check is "which app is frontmost at that
moment", which is as much as macOS records about who wrote to the clipboard:
anything arriving while Apple Books is in front, including Universal Clipboard
content from another device, is treated as copied from Apple Books.

Switching it off stops the checking. Text read this way is transient like the
rest: it is not added to the library or the persistent audio cache, and it
never leaves this Mac.

Deleting ReadEase does not automatically delete its Application Support data.
Users can remove that folder separately after closing the app if they no longer
need their library, models, progress, or cache.
