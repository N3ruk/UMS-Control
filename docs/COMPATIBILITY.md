# Compatibility and verification limits

[Español](es/COMPATIBILIDAD.md)

| Target | Package | Actual verification |
| --- | --- | --- |
| Linux x86-64, glibc 2.35+ | DEB / ZIP | Ubuntu 22.04 and 24.04 isolated userspaces; the host desktop is Linux. See the verification report for package lifecycle checks. |
| Windows 10/11 x86-64 | EXE | Windows PE executable and NSIS installer built; Wine execution and English-interface captures. Native Windows acceptance remains pending. |
| ARM, 32-bit, musl/Alpine, macOS | None | Not supported by these binary packages. |

The ZIP bundles Python, Qt and a private native-library closure based on Ubuntu 22.04. It does not install Debian packages into the operating system and does not require APT/RPM, system Python, pip or a compiler. Linux requires a graphical desktop, compatible graphics drivers and glibc 2.35 or later. More distributions may work, but only actual tested configurations are certified. Clean userspace tests are not physical desktop/systemd-login tests.

Linux uses the systemd user manager when available, or a tracked per-user process otherwise. Windows uses the same application and a tracked per-user process; session autostart is a user Startup entry. PID and process creation time are checked before controlling a process. No administrative Windows service is installed.

Some devices may not be **100% compatible**. Compatibility depends on the device, firmware and media formats, not simply on its manufacturer. Original delivery preserves bytes, not device codec support; protocol tests or a converted stream do not certify physical-device playback.

Discovery is local IPv4. Applications sharing one IP cannot have separate IP-based device profiles. The server host is excluded from discovery. The Windows firewall may require approval for the selected private LAN; the installer does not change firewall rules silently. Wine cannot validate those native Windows interactions.

The bootstrap integration has separate reproducible Linux/Windows builds against the corresponding UMS 15.9.0 JARs and Java 17. Future stable releases are staged, rebuilt against their JAR if necessary, checked and probed before replacement. A future incompatible release may be rejected without replacing the existing installation. Rebuilding an integration requires an appropriate JDK.

NVIDIA encoding needs compatible hardware and drivers. CPU tests do not certify NVENC, HDR, every seek operation, long playback sessions or every media format. Logs, profiles, media and private development diagnostics are excluded from public source exports.

The Windows EXE is a separate testing prerelease, not a stable Linux release asset. See [all pending native Windows checks](WINDOWS-TESTING.md).
