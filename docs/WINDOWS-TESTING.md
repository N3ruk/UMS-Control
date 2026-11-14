# Windows prerelease: partial native acceptance

[Español](es/PRUEBAS-WINDOWS.md)

**Status: testing only.** The public EXE remains [v1.0.0-windows-rc1](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0-windows-rc1), separate from stable Linux. Its assets have not been replaced. The installer/UI version remains 1.0.0.

## Published EXE versus corrected development candidate

Native Windows 11 testing on 2026-11-14 exposed shutdown, session-launcher encoding/ownership and Unicode folder-handling defects in the published RC1. Fixes have been tested in a **private development candidate**, not incorporated into the downloadable EXE. Do not attribute the corrected candidate's results to the published installer.

Earlier Wine checks covered NSIS installation, the panel and preference preservation, but its JNA/SecureRandom limitation prevented a server test. A native Windows 11 build 26300.9974 now runs the real server successfully; that Wine limitation is not a native server failure.

## Checked on native Windows 11

Using a normal, non-administrator account and synthetic media:

- Per-user NSIS installation in a path containing spaces, Spanish and Japanese characters; initial language selection, replacement preserving preferences, frozen executable self-test and clean GUI shutdown.
- Native Qt layout checks: 168 views, six themes and seven languages. These automated checks do not replace manual usability review.
- Official UMS 15.9.0 runtime, native staged Java/JNA probe, healthy localhost administration, start/stop/restart and duplicate-start prevention.
- Corrected frozen GUI repair, server removal and fresh server installation; panel uninstallation preserves preferences, profiles and media. A corrupt archive is rejected without replacing the running runtime. A newer upstream release was not installed.
- Enable/disable ownership checks and actual Windows Script Host launch of the frozen server entry from a Unicode path. **Logoff/login and reboot were not performed.**
- LAN delivery to a separate physical Linux computer: Unicode folder browsing, unrelated-folder exclusion, byte-identical originals, GET/HEAD and byte-range seeking; real Windows FFmpeg manual/automatic transcoding, audio streams and soft/burn subtitle paths. Synthetic clips are not TV/console playback or a subjective audio/subtitle review.
- DLNA reachable from the LAN; administration bound to localhost and inaccessible from the other computer. No firewall rules were changed; a clean-machine firewall prompt/allow/deny flow was not exercised.
- Test installation, data, managed processes, menu/registry/startup entries and temporary files removed; only task-owned files recycled. Existing personal media and the native OpenClaw node were not modified.

Separate full source regressions passed: 163 tests, 168 UI views, four isolated real DLNA scenarios, reproducible Java rebuild and minimal runtime payload checks. These are development results, not a republished binary release.

## Still required before stable Windows acceptance

- [ ] Test a release-ready corrected installer and its exact published source/checksums.
- [ ] Actual session logoff/login with autostart enabled and disabled; reboot/reconnection if claimed.
- [ ] Fresh-machine private-network firewall prompt, allow/deny behaviour and intended adapter selection.
- [ ] Physical TV/console browsing and playback, audio/subtitle selection and seeking; verify multiple configured clients, unconfigured-client and host exclusion on the target network.
- [ ] Sustained playback, setting changes/restart and recovery after interruptions; separately verify NVENC before claiming hardware encoding.
- [ ] A real update to a newer official UMS runtime and recovery from an activation failure.
- [ ] Native Windows 10 validation before claiming both Windows 10 and 11 have been tested.

Windows remains a separate **prerelease**. Some devices may not be fully compatible; testing one system does not certify every device, codec, driver or firmware. Never publish private media, network addresses or unredacted workstation logs.
