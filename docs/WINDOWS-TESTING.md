# Windows prerelease: native acceptance pending

[Español](es/PRUEBAS-WINDOWS.md)

**Status: testing only.** The EXE belongs to [v1.0.0-windows-rc1](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0-windows-rc1). It is not included in the stable Linux v1.0.0 release. The installer/application still reports version 1.0.0; the prerelease tag identifies its acceptance status.

## What has actually been checked

Under **Wine only**: per-user NSIS installation, normal Qt application startup, self-test, English-interface screenshots, language/preferences preservation during same-version replacement, and uninstallation. Separate Windows UMS inputs and Java integration were verified. These results are not native Windows 10/11 validation.

The official Windows JVM and FFmpeg start under Wine, but the disposable UMS server probe fails during JNA/SecureRandom operating-system entropy initialization. This test-environment failure does not establish whether the server works or fails on native Windows. No native Windows machine was available.

## Required before adding Windows to a stable release

All items below are **pending on native Windows 10/11 x86-64**, using a normal non-administrator account. Record the exact Windows build, application checksum, results and any fixes/retests. A result on one Windows version does not certify the other.

- [ ] Install and launch the EXE; select the initial language, change it later, and check paths containing spaces/non-ASCII characters.
- [ ] Replace/reinstall and uninstall the panel; verify settings, profiles and original media are preserved and only the managed server process/autostart entry are affected.
- [ ] Install the official UMS runtime through the panel, pass its staged server probe and reach healthy localhost administration; verify repair, update/failure recovery and managed server removal without deleting user configuration/media.
- [ ] Start, stop and restart the real UMS server; inspect health and logs and verify that no duplicate/orphan managed processes remain.
- [ ] Enable/disable session autostart and log out/in to verify both states without administrator rights.
- [ ] Select the intended IPv4 LAN interface; discover devices and test private-network Windows firewall prompts/permissions, localhost-only administration and DLNA reachability from another physical device.
- [ ] Browse/search from a real DLNA client; verify per-device folder isolation, unconfigured-client exclusion and host exclusion without renaming or modifying source media.
- [ ] Play original media and manual/automatic transcoding on a physical client; check audio/subtitle selection, seeking, restart/application of settings and a sustained session. Check NVENC separately if claiming NVIDIA hardware encoding support.

Once these checks pass and any failures are fixed and retested, the Windows installer may be added to a stable release. Until then it remains a separate **prerelease**, even though its installer and UI work under Wine.

Some devices may not be 100% compatible; these checks do not certify every device, codec or firmware. Do not publish personal media, private addresses or unredacted logs in test reports.
