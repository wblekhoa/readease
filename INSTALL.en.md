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

### Step 3 — First launch

Double-click `ReadEase.app` and use it like any other app. From 0.1.2 the build is signed with an Apple Developer ID certificate and notarized by Apple, so macOS opens it without a dialog. The first launch can take a few seconds while macOS checks the signature.

> **0.1.0 or 0.1.1, downloaded before 15 September 2026,** carried no certificate, so macOS blocks it with *"Apple could not verify ReadEase is free of malware"*. The simplest fix is the current build from the Releases page. To open the old one anyway: **right-click** `ReadEase.app` → **Open** → **Open**. If you double-clicked and see **Move to Trash**, click **Done**, open **System Settings → Privacy & Security**, scroll to **Security** and click **Open Anyway**. That makes an exception for that one app only.

> A dialog saying the app **"is damaged and can't be opened"** means the zip was altered after download (a browser or antivirus rewrote it). Delete it and download again from the official Releases page; do not reach for `xattr` or turn security off.

### Step 4 — Prepare the voice

Open the app and click **Set up voice**. It downloads the Vietnamese voice model — *Standard* is about 330 MB, or *Highest* about 625 MB if you pick it under **Voice quality** just above (a little better, roughly 11% slower). Only the build you pick is downloaded. From here on everything runs on your Mac, no network needed.

### Step 5 (optional) — Read a selection from any app

To select text in a web page, PDF, Apple Books… and press a shortcut to hear it, ReadEase needs the **Accessibility** permission. The first time you use **Read selection**, macOS asks; enable ReadEase under **System Settings → Privacy & Security → Accessibility**. If you never use that feature, no permission is needed.

## Upgrading, removing, where your data lives

- **Upgrade:** download the new zip and drag `ReadEase.app` over the old one. Documents, progress, notes and downloaded voices **are kept** — they live outside the app in `~/Library/Application Support/VieNeu Reader/`. Upgrading from 0.1.0/0.1.1 to 0.1.2 asks you to enable **Accessibility** once more (the app's signature changed from ad-hoc to Developer ID); from 0.1.2 on the permission survives updates.
- **Remove:** drag `ReadEase.app` to the Trash. To remove documents and voices too, delete that folder as well.
- **Cost:** none. The on-device voice is free for good. Only if **you** enter your own OpenAI or ElevenLabs key to use a paid AI voice do you pay that provider, at the price shown in the read button; the app takes nothing.

## Common problems

| You see | It means | Do this |
| --- | --- | --- |
| "Apple could not verify…" | An old build (before 0.1.2) without a certificate | Get the current build, or see the note in Step 3 |
| "…is damaged and can't be opened" | The zip was altered after download | Delete and download again |
| Will not open on an Intel Mac | This build is Apple Silicon only | Not supported yet |
| "Requires macOS 15" | Older macOS | Update macOS |
| The read-selection shortcut reads nothing | Accessibility not granted | Step 5 |
| Voice not ready | Model not downloaded | Step 4 |

Still stuck? Open an issue at <https://github.com/wblekhoa/readease/issues> with your macOS version and the exact text macOS showed.

## How is the app checked?

From 0.1.2 every release is signed with the author's Apple Developer ID certificate and notarized by Apple (Apple scans it for malware and issues a ticket that is stapled to the app). You can check for yourself: in Terminal, run `spctl -a -t exec -vv /Applications/ReadEase.app`; the answer should contain `accepted` and `Notarized Developer ID`. The source stays public so anyone can verify that the app sends your books nowhere.
