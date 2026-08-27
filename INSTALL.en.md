# Install ReadEase — English Guide

This guide is for people who want to install ReadEase from source on a Mac without needing programming experience.

> [Hướng dẫn cài đặt tiếng Việt](INSTALL.md) · [English product guide](README.en.md)

## Before you begin

ReadEase is currently distributed as a local **source build**. `Install ReadEase.command` is not signed with an Apple Developer ID and is not Apple-notarized, so macOS Gatekeeper may block it the first time it opens. This is a macOS distribution warning, not an app crash.

Proceed only with source downloaded from the official repository:

- Repository: <https://github.com/wblekhoa/readease>
- Direct ZIP: <https://github.com/wblekhoa/readease/archive/refs/heads/main.zip>

## Requirements

| Requirement | Details |
| --- | --- |
| Mac | Apple Silicon: M1, M2, M3, M4 or newer |
| macOS | macOS 15 or newer |
| Free disk space | At least 6 GB during the build and installation |
| Internet | Required for the first build and first voice-model download |
| Apple tools | Xcode Command Line Tools |

No API key, Homebrew, Python or `uv` installation is required. The installer prepares a checksum-pinned build environment, does not use `sudo`, does not modify your shell profile and removes temporary build files after a successful installation.

## Step-by-step installation

### Step 1 — Download the source

Click [**Download ReadEase — Source ZIP**](https://github.com/wblekhoa/readease/archive/refs/heads/main.zip). Open the downloaded ZIP to extract the `readease-main` folder.

### Step 2 — Open the installer

Inside `readease-main`, double-click **Install ReadEase.command**.

If Terminal opens and the compatibility check begins, continue to [Step 4](#step-4--install-apples-command-line-tools-if-needed).

### Step 3 — If macOS shows “Not Opened”

You may see this warning:

> “Install ReadEase.command” Not Opened
>
> Apple could not verify “Install ReadEase.command” is free of malware…

Follow these steps in order:

1. Click **Done**. Do **not** click **Move to Trash**.
2. Open **System Settings**.
3. Select **Privacy & Security**.
4. Scroll to **Security** and find the message saying `Install ReadEase.command was blocked…`.
5. Click **Open Anyway**.
6. Authenticate with Touch ID or your Mac login password.
7. When the warning appears again, click **Open**.

The **Open Anyway** option is normally available for about one hour after the blocked launch. If it is missing, double-click `Install ReadEase.command` again and immediately return to **Privacy & Security**.

If you clicked **Move to Trash**, restore the source folder from Trash or download the ZIP again from the official repository.

Apple documents the same flow in [Open a Mac app from an unknown developer](https://support.apple.com/guide/mac-help/mh40616/mac). Use **Open Anyway** only for source you trust. This creates an exception for the selected file and does not require disabling Gatekeeper system-wide.

### Step 4 — Install Apple’s command-line tools if needed

If the installer reports `missing_xcode_tools`, open Terminal and run:

```bash
xcode-select --install
```

Complete Apple’s installer, then open **Install ReadEase.command** again. The full Xcode application is not required.

### Step 5 — Wait for the local build

The first build usually takes 10–25 minutes. The installer will:

1. Check the Mac architecture, macOS version, free disk space and build tools.
2. Download a checksum-pinned build tool if the required version is missing.
3. Build and verify ReadEase locally.
4. Install the app at `~/Applications/ReadEase.app`.
5. Open ReadEase automatically.

Do not close Terminal during installation. A successful run ends with:

```text
READEASE_SOURCE_INSTALL PASS target=.../Applications/ReadEase.app
```

### Step 6 — Set up the Vietnamese voice

In ReadEase, choose `English` from the language selector if needed, then click **Set up voice**. The app downloads about 330 MB of Vietnamese voice data the first time. Reading is local and can work offline afterward.

## Check compatibility without installing

Open Terminal in `readease-main` and run:

```bash
./Install\ ReadEase.command --check
```

A compatible Mac returns a line containing:

```text
READEASE_PREFLIGHT PASS
```

## Ask an AI assistant to install it

Open `readease-main` in an AI tool that can use Terminal and send this prompt:

> Run `./Install ReadEase.command`, diagnose and fix any installation error, then confirm that `~/Applications/ReadEase.app` opens. Do not publish anything or change dependencies.

## Common problems

### Open Anyway is missing

- Double-click the installer so macOS records a new blocked attempt.
- Immediately open **System Settings → Privacy & Security** and scroll to **Security**.
- The option may disappear after about one hour or may be unavailable on a Mac managed by a company or school. Contact the administrator for a managed device.

### `Permission denied`

Open Terminal in the source folder and run:

```bash
chmod u+x "Install ReadEase.command"
./Install\ ReadEase.command
```

This restores the installer’s executable permission; it does not disable Gatekeeper.

### `unsupported_arch`

The Mac uses an Intel processor. The current ReadEase build supports Apple Silicon only.

### `unsupported_macos`

Update the Mac to macOS 15 or newer, then try again.

### `insufficient_disk`

Free enough storage to have at least 6 GB available, then run the installer again.

### Installation stops partway through

Keep the complete Terminal output and send it to the maintainer or an AI assistant. On failure, the installer prints a `READEASE_BUILD_PRESERVED` path and retains the diagnostic environment. After a successful installation, temporary build data is removed automatically.

## Why the warning cannot be removed from this source build

To open normally for every user without **Open Anyway**, a public artifact must be signed with an Apple Developer ID certificate, use the hardened runtime, be submitted to Apple for notarization and be packaged as a release artifact. The current local source build is only ad-hoc signed on the user’s Mac, so the Gatekeeper instructions above remain necessary.
