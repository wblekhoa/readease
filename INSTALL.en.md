# Install ReadEase — Thư Âm

For anyone who wants ReadEase on a Mac without any programming. Free, no account, no API key.

> [Hướng dẫn tiếng Việt](INSTALL.md) · [About the app](README.en.md)

## What you need

| Requirement | Details |
| --- | --- |
| Mac | Apple Silicon: M1, M2, M3, M4 or newer. Intel Macs are not supported yet. |
| macOS | macOS 15 or newer |
| Free disk space | About 220 MB for the app, plus a one-time voice download: *Standard* ~330 MB or *Highest* ~625 MB |
| Internet | Only to download the app and to prepare the voice once. Reading works offline afterwards. |

## Step by step

### Step 1 — Download

Open the [**Releases**](https://github.com/wblekhoa/readease/releases/latest) page and download `ReadEase-<version>-arm64.zip`. Double-click the zip to unpack it — you get `ReadEase.app`.

### Step 2 — Drag into Applications

Drag `ReadEase.app` into **Applications** (or `~/Applications`). That is the whole install. No Terminal, nothing else to set up.

### Step 3 — First launch: get past the macOS warning

This build carries **no Apple Developer certificate** and is not notarized, so the first launch is blocked with *"Apple could not verify ReadEase is free of malware"*. That is Gatekeeper's message for apps from unregistered developers, not a broken app. You do this **once**.

**Quick way:** **right-click** (or Control-click) `ReadEase.app` → **Open** → click **Open** again in the dialog.

**If you double-clicked** and the dialog offers **Move to Trash**:

1. Click **Done**. **Do not click Move to Trash.**
2. Open **System Settings** → **Privacy & Security**.
3. Scroll to **Security** and find *"ReadEase" was blocked…*
4. Click **Open Anyway** and confirm with Touch ID or your login password.
5. Open the app again; when asked once more, click **Open**.

**Open Anyway** is shown for about an hour after the blocked attempt. If it is missing, double-click the app once more and return to **Privacy & Security**. Apple documents the same flow in [Open a Mac app from an unknown developer](https://support.apple.com/guide/mac-help/mh40616/mac). This makes an exception for this one app; it does not switch Gatekeeper off.

> A dialog saying the app **"is damaged and can't be opened"** is a different thing: the zip was altered after download (a browser or antivirus rewrote it). Delete it and download again from the official Releases page; do not reach for `xattr` or turn security off.

### Step 4 — Prepare the voice

Open the app and click **Set up voice**. It downloads the Vietnamese voice model — *Standard* is about 330 MB, or *Highest* about 625 MB if you pick it under **Voice quality** just above (a little better, roughly 11% slower). Only the build you pick is downloaded. From here on everything runs on your Mac, no network needed.

### Step 5 (optional) — Read a selection from any app

To select text in a web page, PDF, Apple Books… and press a shortcut to hear it, ReadEase needs the **Accessibility** permission. The first time you use **Read selection**, macOS asks; enable ReadEase under **System Settings → Privacy & Security → Accessibility**. If you never use that feature, no permission is needed.

## Upgrading, removing, where your data lives

- **Upgrade:** download the new zip and drag `ReadEase.app` over the old one. Books, progress, notes and downloaded voices **are kept** — they live outside the app in `~/Library/Application Support/VieNeu Reader/`.
- **Remove:** drag `ReadEase.app` to the Trash. To remove books and voices too, delete that folder as well.
- **Cost:** none. The on-device voice is free for good. Only if **you** enter your own OpenAI or ElevenLabs key to use a paid AI voice do you pay that provider, at the price shown in the read button; the app takes nothing.

## Common problems

| You see | It means | Do this |
| --- | --- | --- |
| "Apple could not verify…" | Gatekeeper; the app is not registered with Apple | Step 3 |
| "…is damaged and can't be opened" | The zip was altered after download | Delete and download again |
| Will not open on an Intel Mac | This build is Apple Silicon only | Not supported yet |
| "Requires macOS 15" | Older macOS | Update macOS |
| The read-selection shortcut reads nothing | Accessibility not granted | Step 5 |
| Voice not ready | Model not downloaded | Step 4 |

Still stuck? Open an issue at <https://github.com/wblekhoa/readease/issues> with your macOS version and the exact text macOS showed.

## Why the first-launch warning at all?

Opening like any other app, with no Open Anyway step, needs an Apple Developer ID signature and Apple notarization. ReadEase is a free personal project and has not done that; in exchange you have the full source to check for yourself that the app sends your books nowhere.
