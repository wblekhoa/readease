[app]
title = ReadEase
project_dir = ..
input_file = app_main.py
exec_directory = dist
project_file =
icon = assets/branding/readease.icns

[python]
python_path = .venv/bin/python

# Deliberately empty: build-app.sh refuses to let pyside6-deploy install
# undeclared tools. Nuitka 4.1.1 is approved and locked by uv.
packages =
android_packages =

[qt]
qml_files =
excluded_qml_plugins =
modules = Concurrent,Core,DBus,Gui,Multimedia,Network,Pdf,Widgets
plugins = accessiblebridge,egldeviceintegrations,generic,iconengines,imageformats,multimedia,networkaccess,networkinformation,platforms,platforms/darwin,platformthemes,styles,tls,wayland-decoration-client,wayland-graphics-integration-client,wayland-shell-integration,xcbglintegrations

[android]
wheel_pyside =
wheel_shiboken =
plugins =

[nuitka]
macos.permissions =
mode = standalone
extra_args = --quiet --disable-cache=ccache --noinclude-qt-translations --nofollow-import-to=librosa --nofollow-import-to=soxr --nofollow-import-to=soundfile --nofollow-import-to=kaldi_native_fbank --include-package-data=vieneu:assets/voices_v3_turbo.json --include-package=vieneu_reader --macos-app-name=ReadEase --macos-signed-app-name=vn.dolenglish.vieneureader --macos-app-version=0.1.0 --macos-target-arch=arm64 --report=dist/nuitka-compilation-report.xml

[buildozer]
mode = debug
recipe_dir =
jars_dir =
ndk_path =
sdk_path =
local_libs =
arch =
