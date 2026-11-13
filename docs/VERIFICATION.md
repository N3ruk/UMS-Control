# Verification of UMS Control 1.0.0

[Español](es/VERIFICACION.md)

These are historical checks of the published release. Full regression/UI/DLNA harnesses are maintained privately and are not needed to run or build the application. Current public CI validates the minimal source allowlist, compilation, application self-test and Java rebuild; it does not rerun the private release acceptance suite.

The [Linux v1.0.0 release](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0) contains the DEB and ZIP. The Windows EXE is a separate [v1.0.0-windows-rc1 prerelease](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0-windows-rc1), pending the [native Windows acceptance checklist](WINDOWS-TESTING.md). Publishing Linux does not certify Windows or universal device compatibility.

| Check | Result |
| --- | --- |
| Source regressions in an isolated Ubuntu 24.04 userspace | 160 tests passed; integration required, no skipped integration |
| UI matrix | 168 views: six themes, seven languages, two sizes, two main tabs |
| Linux portable backend | Actual isolated install, start, restart, enable/disable session autostart, stop and removal of a disposable UMS runtime passed |
| DEB package lifecycle | Install, same-version replacement and purge passed in isolated Ubuntu 24.04; English interactive prompt, initial German/French selection and preservation of a saved Japanese preference verified |
| ZIP package lifecycle | Install, same-version replacement and removal passed in isolated Ubuntu 22.04 without system Python/Qt; initial French selection and preservation verified |
| Windows EXE under Wine | Actual NSIS install, normal executable startup, self-test, same-version replacement and uninstall passed; saved Japanese preference preserved |
| Java integration | Separate official Linux/Windows input JARs verified; matching Windows bootstrap rebuilt identically with JDK 17 |
| English screenshots | Linux: real Qt renders of all six themes from the DEB payload in an isolated userspace. Windows: EXE-installed app under Wine; synthetic device profiles, no private media |

## Acceptance still required

**Native Windows 10/11 server operation is not validated.** The official Windows JVM and FFmpeg executables start under Wine, but the staged UMS server probe fails while obtaining operating-system cryptographic entropy through JNA/SecureRandom. This is a concrete limitation of the available test environment; it is not proof that native Windows works or fails. No Windows host was available. Do not present the Windows candidate as a fully accepted stable release until installation, server start/restart/stop, session autostart, discovery, administration, DLNA delivery and firewall interaction pass on native Windows.

A real clean Linux graphical login with its systemd user manager, distribution-specific desktop/driver combinations, physical device playback, NVENC and long sessions are not replaced by userspace/synthetic tests. Linux package checks cover Ubuntu 22.04/24.04 userspaces; other glibc 2.35+ distributions are compatibility targets, not individually certified systems.

Some devices may not be 100% compatible. No manufacturer is classified as incompatible.

Private logs and workstation-state snapshots remain outside the public source allowlist. The binary SHA256SUMS is generated after final packaging; the source packaging/source-manifest.json records the exact public source files.

Linux ELF audit: 470 files checked, maximum required GLIBC symbol version 2.35.
