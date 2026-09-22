# The disk image's window, for dmgbuild (`build-release-app.sh` runs it
# through `uvx`): the app on the left, Applications on the right, the
# arrow drawn between them by `assets/branding/dmg-background.png` (and
# its @2x twin, which dmgbuild folds into one HiDPI TIFF). The two icon
# slots below are the ones the picture is drawn around - move one, move
# the other. Nothing here opens a Finder window: dmgbuild writes the
# .DS_Store itself and mounts with -nobrowse.
#
#   uvx --from dmgbuild dmgbuild -s scripts/dmg-settings.py \
#       -D app=path/to/ReadEase.app -D background=assets/branding/dmg-background.png \
#       -D icon=app/src-tauri/icons/icon.icns ReadEase out.dmg

app = defines["app"]  # noqa: F821 - dmgbuild injects `defines`
background = defines["background"]  # noqa: F821
icon = defines.get("icon")  # noqa: F821 - the volume's own icon, when given

format = "UDZO"
# APFS, not dmgbuild's HFS+ default. HFS+ stores filenames normalised to
# NFD; the sidecar ships voice samples whose names carry Vietnamese
# diacritics ("Bình (nam miền Bắc).pt"), the code signature seals those
# names as written, and after normalisation codesign reads every one as a
# file ADDED to the bundle and the sealed one as missing. Apple's notary
# answered "The signature of the binary is invalid" for 0.1.14's first
# image; the 0.1.13 image, made by `hdiutil create -srcfolder` (APFS by
# default on macOS 15), verified clean. Verified again by the mount check
# in build-release-app.sh, which now runs before any notarisation.
filesystem = "APFS"
files = [app]
symlinks = {"Applications": "/Applications"}

# The window: where it opens and how big its content area is - the size
# of the background picture.
window_rect = ((200, 120), (660, 400))
default_view = "icon-view"
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
sidebar_width = 0

# Icons: large, labelled underneath, on the two slots the picture leaves.
icon_size = 128
text_size = 13
label_pos = "bottom"
show_icon_preview = False
arrange_by = None
scroll_position = (0, 0)
icon_locations = {
    "ReadEase.app": (165, 175),
    "Applications": (495, 175),
}
