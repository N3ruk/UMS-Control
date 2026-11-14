# Windows 1.0.0 — stable verification

[Español](es/PRUEBAS-WINDOWS.md)

The Windows x86-64 installer is part of the [UMS Control 1.0.0 stable release](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0), alongside Linux DEB/ZIP. Installation is per user, without administrator rights. Existing settings, device profiles and shared folders are preserved.

## Native Windows 11 checks

- Per-user installation/replacement, language preservation, Unicode paths, executable self-test and clean GUI shutdown.
- Official UMS 15.9.0 startup, health, stop/restart, repair and duplicate-start prevention.
- Physical Ethernet/Wi-Fi detection; virtual and disconnected adapters excluded.
- Windows-specific launcher encoding and folder-path handling.
- Catalogue association with the explicitly configured IP when a TV changes its UPnP UUID; configured UUIDs retain priority.
- Custom device names remain visible after reopening and renderer identity changes.
- Windows icon in the application, installer, uninstaller and shortcuts.

## User-confirmed playback and session acceptance

On 2026-11-14 the user confirmed TV browsing/playback, pause/resume and seeking, followed by the final corrected version's reboot/autostart ON and OFF checks and sustained playback with audio, subtitles and alternative tracks. These are user-reported physical-device results, separate from automated measurements.

## Packaging and automated verification

The final stable installer retains the corrected executable accepted on native Windows and includes the current stable documentation. Source regressions passed 170 tests; the interface matrix covered 168 views and five isolated DLNA scenarios passed. Java rebuild and minimal runtime checks passed. Final installer install/replacement, self-test, GUI startup/shutdown, icons and preference-preserving removal are checked separately from native playback acceptance.

Windows 11 is the natively verified system; Windows 10 is a compatibility target. Device, codec, firmware and driver compatibility varies. Hardware encoding needs suitable hardware and drivers; these results are not a universal playback guarantee. Private profiles, media, addresses and workstation logs are not published.
