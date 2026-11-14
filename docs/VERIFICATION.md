# Verification of UMS Control 1.0.0

[Español](es/VERIFICACION.md)

The [stable v1.0.0 release](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0) includes Linux DEB/ZIP, the Windows installer and a common SHA256SUMS. Full regression/UI/DLNA harnesses remain private; public CI checks integrity, Python compilation, application self-test and reproducible Java integration.

| Check | Result |
| --- | --- |
| Source regressions | 170 tests passed in isolated Ubuntu 24.04 |
| Interface matrix | 168 views: six themes, seven languages, two sizes, two main tabs |
| DLNA integration | Five isolated scenarios passed, including UPnP-first catalogue lookup |
| Linux DEB/ZIP | Install/replacement, self-test, UI and removal preserving preferences; Ubuntu 22.04/24.04 userspaces |
| Linux compatibility | 479 ELF files audited; maximum GLIBC symbol requirement 2.35 |
| Native Windows | Windows 11 installation, server lifecycle, physical adapters, catalogue and custom names |
| Physical Windows acceptance | User confirmed TV, pause/seeking, sustained audio/subtitle/alternative-track playback, reboot and autostart ON/OFF |
| Final Windows packaging | Native-accepted executable retained; stable documentation, installer lifecycle, self-test, GUI and icons checked |
| Java | Separate Linux/Windows inputs and matching integration; JDK 17 reproducible rebuild |
| Screenshots | Linux: real Qt renders from DEB payload. Windows: installed EXE under Wine. Demonstration data only |

See [Windows verification](WINDOWS-TESTING.md) for automated versus user-reported results. Windows 11 is natively verified; Windows 10 is a compatibility target. Linux requires x86-64, glibc 2.35+ and X11/Wayland; other distribution/driver combinations are not individually certified. Device/media compatibility varies.

Private logs, profiles and media are excluded. `packaging/source-manifest.json` identifies public sources. Corresponding sources and build recipes remain in the repository; release attachments contain packages/checksums, not an extra source ZIP.
