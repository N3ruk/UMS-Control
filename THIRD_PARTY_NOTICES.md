# Third-party software and resource provenance

UMS Control 1.0.0 candidate — Copyright (C) 2026 N3ruk — frontend GPL-3.0-or-later. Independent frontend; not an official Universal Media Server product.

## Files actually redistributed in the public source candidate

- Original frontend Python/UI catalogs: GPL-3.0-or-later. Windows geometric artwork: GPL-3.0-or-later, editable source `tools/render_assets.py`, inventory `assets/windows/ORIGIN.md`. Linux icon and wallpapers are supplied artwork selected by N3ruk, preserved byte-for-byte; provenance and SHA256 are in `assets/ORIGIN.md`. The frontend license does not claim authorship of or relicense any third-party imagery.
- Modified Universal Media Server Java files under `patches/net` and compiled `server-support/update.jar` / `update-windows.jar`: retain their upstream GPL-2.0 notices and authorship; see `patches/LICENSE.UMS.txt`. Complete modified files, exact upstream source reference/archive/hash, verified official build input and deterministic build recipe are provided. See `server-support/upstream.json` and `docs/public/BUILD.md`. This notice does not relicense the upstream Java code as frontend code.
- `baul.svg`: original geometric development icon, GPL-3.0-or-later; retained for source-install compatibility.

## Downloaded or system-provided, not redistributed in this public source tree

- Universal Media Server 15.9.0, based on PS3 Media Server: GPL-2.0, <https://github.com/UniversalMediaServer/UniversalMediaServer>. The official archive/JAR are downloaded with verified hashes and never edited. Java, FFmpeg and other upstream runtime components remain within that upstream distribution, with their own notices, source obligations and licenses.
- MediaInfo 24.01+dfsg-1build2 (BSD-2-Clause), Zen 0.4.41-2.1build1 (Zlib), TinyXML2 10.0.0+dfsg-2 (Zlib), libmms 0.6.4-3build1 (LGPL-2.0-or-later): downloaded directly from Ubuntu's official archive, hash-pinned in `server-support/dependencies.json`. Exact binary copyright files are retained when extracted under `native/usr/share/doc`. The lock also lists corresponding `.dsc`, original source and distribution patches, URLs/hashes/sizes. `native_dependencies.py --sources` fetches these verified sources. The lock inventories all license labels from each package copyright file, including bundled code and distribution changes (not only the principal library license). Distribution packaging contains additional copyright notices; the extracted copyright files are authoritative.
- PyQt6 and Qt6: system dependencies for source execution; the binary distributions vendor the locked runtime described below. PyQt6 is used under its GPL license. Qt6 retains its own LGPL/GPL/commercial licensing options. Qt translation catalogs come from the distribution `qt6-translations-l10n` package; private cached catalogs are not in public exports.
- Fonts used for rendering the UI or synthetic tests are system dependencies, not copied into the application distribution. Test media is generated from FFmpeg test patterns and sine tones, not user files.

No user media, network credentials, profiles, private logs or developer diagnostics are part of the public application source. The binary distributions additionally carry the component inventories and license notices described below; the source export does not contain the complete downloaded runtimes.

## Binary panel distributions

DEB/ZIP include a private CPython runtime from python-build-standalone (PSF and bundled-component licenses), PyQt6 6.5.3 (GPLv3), Qt 6.5.3 (LGPLv3/GPL exceptions as applicable), PyQt6-sip 13.10.2, psutil 7.2.2 (BSD), Send2Trash 2.1.0 (BSD) and zstandard 0.25.0 (BSD). Their exact artifact URLs and SHA256 are in `packaging/inputs.json`; wheel distribution metadata contains license texts. Python runtime licenses are retained. Sources: https://github.com/python/cpython , https://github.com/astral-sh/python-build-standalone , https://www.riverbankcomputing.com/static/Downloads/PyQt6/ , https://download.qt.io/archive/qt/6.5/6.5.3/ , https://github.com/giampaolo/psutil , https://github.com/arsenetar/send2trash , https://github.com/indygreg/python-zstandard .

Windows uses CPython 3.12.10, the corresponding Windows Qt/PyQt/psutil wheels and the PyInstaller bootloader (GPL with its distribution exception). The included 7-Zip 26.06 extractor retains its license (LGPL/BSD/unRAR restriction where applicable); exact installer input is pinned in `packaging/inputs.json`. 7-Zip corresponding source: https://github.com/ip7z/7zip/releases/tag/26.06 .

Linux library closure is copied from the prepared Ubuntu 22.04 build base; its package copyright notices must be retained in the binary license directory and source/package versions recorded in the binary manifest. Corresponding Ubuntu source packages: https://archive.ubuntu.com/ubuntu/pool/ . The explicitly downloaded MediaInfo/Zen/TinyXML2/libmms source inputs are pinned in `server-support/dependencies-portable.json`. No system libc or graphics driver is bundled.

UMS itself is downloaded separately after an explicit user action. Its upstream licenses and binary notices remain in the managed runtime. The matching modified Java integration sources are shipped in `patches/`; the official UMS JAR remains unmodified.
