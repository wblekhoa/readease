# ReadEase — Thư Âm

ReadEase is a local-first macOS app that reads text-based PDFs, reflowable EPUBs and pasted text with Vietnamese VieNeu-TTS. It requires **no API key**, sends no book content to a server and works offline after the first voice-model setup.

> [Đọc tài liệu tiếng Việt](README.md) · [Full English installation guide](INSTALL.en.md)

## Download ReadEase

### [⬇️ Download the latest Source ZIP](https://github.com/wblekhoa/readease/archive/refs/heads/main.zip)

This link downloads the latest source from `main`. ReadEase is currently distributed as a local source build, not as a notarized `.dmg` or public binary release.

> [!IMPORTANT]
> macOS may show **“Install ReadEase.command” Not Opened** because this source build is not Apple-notarized. Click **Done**, not **Move to Trash**, then open **System Settings → Privacy & Security → Security → Open Anyway**. Follow the [step-by-step English installation guide](INSTALL.en.md).

## System requirements

| Requirement | Details |
| --- | --- |
| Mac | Apple Silicon: M1, M2, M3, M4 or newer |
| macOS | macOS 15 or newer |
| Free disk space | At least 6 GB during the build and installation |
| Internet | Required for the first build and first voice-model download |
| Apple tools | Xcode Command Line Tools |

You do not need an API key, Homebrew, Python, `uv` or programming knowledge. The installer downloads its checksum-pinned build environment, does not use `sudo`, does not modify your shell profile and removes temporary build files after a successful installation.

## Quick installation

1. [Download the Source ZIP](https://github.com/wblekhoa/readease/archive/refs/heads/main.zip) and extract it.
2. Open `readease-main` and double-click **Install ReadEase.command**.
3. If Gatekeeper blocks it, click **Done**, then use **System Settings → Privacy & Security → Security → Open Anyway**.
4. If the installer reports missing Apple developer tools, run `xcode-select --install`, complete Apple’s installer and open **Install ReadEase.command** again.
5. Wait about 10–25 minutes. ReadEase is built and checked locally, installed at `~/Applications/ReadEase.app` and opened automatically.
6. In ReadEase, click **Set up voice** once to download about 330 MB of Vietnamese voice data.

See [INSTALL.en.md](INSTALL.en.md) for screenshots-message wording, Gatekeeper details, compatibility checks and troubleshooting.

## Main features

- **Book library:** import text-based PDFs and reflowable EPUBs, save reading progress and continue later.
- **In-app reader:** choose a chapter, read continuously by paragraph or read only selected text.
- **EPUB figures:** show meaningful local raster images in reading order, number them as **Figure 1, Figure 2…**, and add a spoken cue at the correct position.
- **Paste text:** paste up to 100,000 characters while preserving paragraph boundaries; long passages are split into manageable playback parts.
- **Read from Apple Books:** select text and press the read shortcut (**Control-Option-Command-R** by default, changeable in the **Read books** view) without bringing ReadEase to the foreground.
- **Session history:** replay up to 10 recent items from books, pasted text or Apple Books. History disappears when the app closes.
- **Vietnamese and English UI:** choose `🇻🇳 Tiếng Việt` or `🇬🇧 English` from the language selector. The choice is applied immediately and saved for the next launch.
- **Local-first privacy:** books, progress, model data and audio cache stay on the Mac. There is no API key, telemetry or background server.

The English option translates the app interface, status messages and common import errors. VieNeu remains a Vietnamese TTS model; switching the UI language does not install an English speech model.

## Using ReadEase

### Read a PDF or EPUB

1. Open ReadEase from `~/Applications`.
2. Choose **Library → Open PDF or EPUB**, or drag a supported file into the window.
3. Select a book and chapter, then click **Read** for continuous playback.
4. Select text in the reader and click **Read selection** to hear only that passage.
5. Use **Previous**, **Next**, **Stop**, voice and speed controls in the player.

For reflowable EPUBs, ReadEase displays text and local raster images in reading order. Small decorative images are ignored to avoid unnecessary spoken cues.

### Read pasted text

1. Choose **Paste text**.
2. Paste the content and select a voice and speed.
3. Click **Read text**. Long text shows progress such as **Reading part 2/7**.

Pasted text stays in the current session, does not become a library book and does not change saved book progress.

### Read selected text from Apple Books

1. Open the **Read books** view in ReadEase to confirm shortcut status.
2. Open Apple Books and select the text you want to hear.
3. Press the read shortcut shown in the **Read books** view (**Control-Option-Command-R** unless you changed it).
4. The first time, enable ReadEase in **System Settings → Privacy & Security → Accessibility**. Use **Open permission settings** in ReadEase to open the correct pane directly.

For each shortcut transaction, ReadEase keeps an in-memory copy of the current clipboard, sends the copy command to Apple Books, then restores every clipboard item/type/byte before reading. If restoration cannot be verified, the app stops before playback. ReadEase does not monitor the screen in the background.

ReadEase does not watch the clipboard either, unless you switch on **Read as soon as you copy in Apple Books** in the **Read books** view. While that is on, ReadEase checks the clipboard's change counter a few times a second and reads newly copied text **while Apple Books is the frontmost app**; it reads only when Apple Books is in front at two consecutive checks, and skips items marked concealed, which password managers set. macOS does not record which app did the copying, so a gap remains: copying elsewhere and switching to Apple Books inside the same fraction of a second can still be read. Switching it off stops the checking. See [`PRIVACY.md`](PRIVACY.md) for details.

### Replay recent content

Open **Session history** in the player to replay recent content. Exact duplicates are grouped, history can be cleared immediately and the entire list disappears when ReadEase closes.

## Local data and privacy

ReadEase stores imported books, reading progress, voice-model data and audio cache at:

```text
~/Library/Application Support/VieNeu Reader/
```

The legacy directory name is intentionally preserved so existing users do not lose their library or progress. Pasted or selected text is not added to the library, written to logs or stored in the audio cache. The first voice-model setup requires the internet; reading is local afterward.

See [PRIVACY.md](PRIVACY.md) for the full privacy boundary.

## Current limitations

- Image-only scanned PDFs require OCR before import; ReadEase does not include OCR yet.
- Password-protected PDFs, DRM-protected EPUBs and damaged files are not supported.
- The EPUB reader does not reproduce every book stylesheet/layout, interactive SVG, complex table or fixed-layout publication.
- The external read-selection shortcut currently supports Apple Books only.
- VieNeu provides Vietnamese speech. English UI support does not add an English voice model.
- The source build is ad-hoc signed on the user’s Mac and is not a Developer ID-signed, notarized public binary.

## Local development

Contributors should use the project’s locked `uv` environment and Python 3.13:

```bash
git clone https://github.com/wblekhoa/readease.git
cd readease
uv sync --locked --managed-python --python 3.13
./scripts/verify.sh
```

`uv.lock` is the dependency source of truth. Do not commit model weights, copyrighted books, generated audio, databases, caches or user data. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Troubleshooting

1. For a Gatekeeper **Not Opened** warning, follow [INSTALL.en.md](INSTALL.en.md), not a system-wide Gatekeeper bypass.
2. If voice setup fails, check the internet connection and click **Try again**.
3. If book import was interrupted, reopen the same source file; ReadEase never deletes the original book.
4. For a repeatable crash, keep the newest report from `~/Library/Logs/DiagnosticReports/` for diagnosis.

## License

First-party source, documentation and application framework are available under [PolyForm Noncommercial 1.0.0](LICENSE) for permitted noncommercial use. ReadEase, modified versions or products based on this first-party framework may not be commercialized without a separate written license from the applicable copyright owner. This is source-available software, not an OSI-approved open-source license.

VieNeu, MOSS and other dependencies retain their own licenses. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [`legal/`](legal/) and [PRIVACY.md](PRIVACY.md). Every source/app build carries the static provenance ID `READEASE-THU-AM-NC-2026-01`; it contains no user information, makes no network connection and performs no tracking.

### 5. Move notes to another copy of a book

The **Move notes** tab reads your Apple Books library to show which notes and highlights would carry over to another copy of the same book. Once you have previewed them, **Copy across** moves them for real. It reads only when you open that tab, and writes only when you press that button - after a preview of that exact pair and a confirmation naming the count. It only copies notes whose chapter is byte-for-byte identical between the two copies - two files can share an edition id and still differ inside, and copying on that assumption puts highlights on the wrong words; the rest stay listed but are not copied. Before writing it backs up your Apple Books data to `~/Library/Application Support/VieNeu Reader/AppleBooksBackups/`; it only ever **adds** to the target book, never edits or deletes, and leaves the source book untouched. Apple Books has to be closed for the copy to run. If Apple Books syncs with iCloud, the copied notes appear on your other devices too. Details in [`PRIVACY.md`](PRIVACY.md).
