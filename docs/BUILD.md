# Build and verification

[Español](es/CONSTRUCCION.md)

## Source and runtime integration

Python 3.12+, PyQt6, psutil, Send2Trash and zstandard are needed for source execution. Application modules and translations are in `src/`; resources stay in `assets/`, `patches/` and `server-support/`. From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python src/launcher.py
```

`python src/install.py` is the optional developer/source installer; release end users use the DEB, ZIP or EXE instead. Do not build from a private development tree containing user logs or profiles.

The public repository contains only application sources, documentation, artwork and build/publication tools. Full regression, UI-matrix and DLNA integration checks are maintained privately; they are not required to run or package the program. Public CI checks source integrity, Python compilation, application self-test and a Java rebuild. Historical release validation is recorded in [VERIFICATION.md](VERIFICATION.md).

The bootstrap Linux JAR and the separately compiled Windows JAR are pinned by SHA256 in `src/server_releases.py`. The integration source is in `patches/net`. A JDK 17 compiler is required for reproducible bootstrap bytecode; JDK 21 with `--release 17` is not equivalent. Windows must be compiled against the official **Windows** UMS JAR. Use `python3 patches/build.py --platform windows --ums-jar OFFICIAL_WINDOWS_UMS_JAR --output server-support/update-windows.jar` for the pinned Windows bootstrap (omit `--platform windows` for Linux). The official JAR is never modified. `tools/update_bundle.py` refreshes checksums only after an intentional input revision.

## Linux DEB and ZIP

`packaging/inputs.json` pins the standalone Python archive and exact wheels by URL/size/SHA256. `server-support/dependencies-portable.json` pins Ubuntu 22.04 native packages and their source packages. A prepared Ubuntu 22.04 build root supplies the closure of desktop/native libraries; system libc and drivers are not bundled. The application separates its library environment from external desktop/system commands.

```sh
python3 packaging/prepare_inputs.py
python3 packaging/build_linux.py --base /absolute/path/to/prepared-ubuntu22-build-root
```

The build root needs `libcurl3-gnutls` and the usual X11/XCB/Wayland/fontconfig/OpenGL loader libraries. Build tooling additionally needs `bwrap`, `dpkg-deb` and an xz-capable compressor. These are build requirements, not Python requirements for end users.

Outputs in `dist/`: `ums-control_1.0.0-1_amd64.deb` and `ums-control-1.0.0-linux-x86_64.zip`. Debian configuration is an English debconf selection. ZIP installation uses the same seven language codes and an English terminal prompt; `./install.sh --language en` is the explicit unattended alternative. The selected default never overwrites saved preferences.

Linux artwork is copied unchanged from `assets/`. The Windows builder overlays `assets/windows/` and does not use the Linux wallpapers. Source export copies both sets verbatim; `tools/render_assets.py` is only for explicitly regenerating Windows geometric artwork, never Linux assets.

## Windows EXE

```sh
python packaging/prepare_inputs.py --windows
```

The preparation command installs only the verified locked wheel contents into the embedded build Python; no system pip installation is needed. The builder requires the `7z` archive tool in PATH. PyInstaller 6.16.0 requires a compatible pefile version; the lock contains 2023.2.7, not the excluded 2024.8.26. Install NSIS build tooling, then run:

```sh
python packaging/build_windows.py
```

Cross-building on Linux uses the prepared Windows Python under Wine and NSIS in the isolated Ubuntu root:

```sh
python3 packaging/build_windows.py --wine-python /absolute/path/windows-python/python.exe --nsis-root /absolute/path/ubuntu24-root
```

The installer is per user, does not run the upstream UMS installer and does not register a system server service. The 7-Zip extractor used for staged UMS installation is included with its license. The application and uninstaller operate only on tracked, owned processes/files. Settings, profiles, server binaries and media are outside the panel installation directory.

## Acceptance and screenshots

Run `ums-control --self-test` on Linux or `UMS-Control.exe --self-test --report result.json` on Windows. The normal startup path can be checked with `--smoke-gui --report result.json`. Demonstration captures use `--screenshots OUTPUT_FOLDER`; they do not apply server settings and must be labelled as demonstration data.

Test actual package install/update/removal in disposable users/systems. Verify language selection and preservation, real server start/stop/restart/autostart and protocol delivery. A clean rootless userspace is not a physical graphical/systemd login test. Wine verifies the Windows artifact but does not certify native Windows networking/firewall/device playback. Windows 1.0.0 stable includes the corrected native executable. See [Windows verification](WINDOWS-TESTING.md).

Never publish private `.cache` trees or workstation configuration. `packaging/public-files.json` lists public sources; `packaging/runtime-files.json` maps only files needed in installed packages. Build/CI/regression tools are not copied into the Linux payload. Refresh `packaging/source-manifest.json` with `python3 tools/export_public.py --update-manifest` after reviewing intentional source changes, then run `python3 tools/export_public.py --check`. Export to a new empty directory using `--destination OUTPUT_FOLDER`. Review artifact SHA256SUMS before publishing.

Sources and build recipes are available in the repository and v1.0.0 tag. Release attachments contain Linux DEB/ZIP, the Windows installer and SHA256SUMS, without an extra source ZIP.

The application EXE, installer and uninstaller embed `assets/windows/ums-control.ico`, a multi-resolution derivative of the Windows PNG. Menu shortcuts and Installed Apps use that icon; the running GUI has a dedicated Windows application identity. The builder accepts `--output`, `--build-dir` and `--inputs-dir` for isolated candidate builds. On Linux, build/output paths must remain inside the source root. Runtime resources are copied only from `packaging/runtime-files.json`.
