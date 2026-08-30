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

Pasted text and text read from a selection are transient. They are not added
to the library or persistent audio cache. The recent-reading list is held in
memory and disappears when ReadEase exits.

## Network use

Network access is used only when the user explicitly prepares the local VieNeu
model. The backbone and codec are downloaded from the public model repositories
at the exact revisions listed in `legal/MODEL_PROVENANCE.md`. Once both are
verified locally, speech initialization fails closed on any remote lookup.

## Apple Books library

The **Move notes** tab reads Apple Books' own databases so it can show which of your
notes and highlights could carry over between two copies of a book. It reads the list
of books and, for the two books you pick, the annotations on them: their positions, the
text you highlighted, and the notes you wrote. Both books are read because the preview
says which notes are already on the other side; they come out of one read, and no other
book in your library is read at all.

Nothing is read until you open that tab. Previewing never opens the originals for
writing: ReadEase copies the database files, reads the copy, and deletes it.

Previewing also opens the two book files themselves. A note's position is recorded as
a count of elements inside one chapter, so it only means the same thing in the other
copy when that chapter is the same document — two files can share an edition id and
still differ inside. ReadEase reads each book's package listing to learn its chapter
order, then takes a checksum of each chapter to compare the two. Chapter text is
hashed, never stored, never shown, and never leaves this Mac; only the two books you
picked are opened.

**Copy across** does write to Apple Books, and it is the only thing in ReadEase that
writes to data belonging to another app. Apple does not support this, so it is built
to be undone:

- It only runs when you press the button, after a preview of that exact pair of books,
  and after a confirmation naming the book and the number of items.
- It refuses while Apple Books is running, because Apple Books would overwrite the
  change.
- It copies the annotation database and its journal files into
  `~/Library/Application Support/VieNeu Reader/AppleBooksBackups/` before writing anything.
  The five most recent are kept and older ones are removed after a successful copy, so
  snapshots of your annotations do not pile up there indefinitely. Deleting that folder
  yourself is safe; it only costs the ability to go back.
- It only copies notes whose chapter is byte-for-byte the same document in both books.
  Anything else stays listed, marked, and unwritten - copying it would put a highlight
  on the wrong words.
- It only ever inserts. The book the notes came from is not modified, and nothing is
  deleted or edited in any book. The book files are never written to at all.
- It skips anything already there, so pressing it again copies nothing rather than
  making a second set. A note already at that position in the target book is left as
  it is, including one you wrote yourself.
- The whole copy is one transaction, so if it fails part way through, your library is
  left exactly as it was.

If Apple Books syncs with iCloud, notes copied this way sync to your other devices like
any other annotation. The confirmation says so before you agree.

That also bounds what the backup can undo. Restoring it puts this Mac's database back,
which is a clean undo only while Apple Books has not launched and synced since the
copy. Once it has, the copied notes exist in iCloud too and Apple Books will bring them
back; from that point the way to remove them is to delete them inside Apple Books,
where they are easy to find - they are the newest annotations on the book you copied
into, and nothing else in that book was touched.

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
