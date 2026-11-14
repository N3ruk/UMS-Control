# Usage

1. Install the panel as described in the README. Open Overview, install the server, then start it. Installation and startup are distinct actions; session autostart is optional.
2. In Devices, search the LAN or add a device by local IPv4. Newly created profiles share nothing. Select a device and add its shared folders; media must already be mounted and readable.
3. Choose Original to deliver unchanged files without conversion caps. Manual conversion uses the selected folder rules; Automatic adapts when needed. Conversion modes place videos inside Transcode, including a no-transcoding original option.
4. Configure audio/subtitles and quality only when converting. Changing maximum resolution suggests a bitrate; a later manual choice is kept until resolution changes again. Switching profiles does not overwrite saved bitrate choices.
5. Compatible announced names change DLNA titles/URLs, not filenames. Folder exceptions and reinclusions apply only to that device. Copying settings preserves the destination device identity and folder rules.
6. Save and apply to activate playback changes. This restarts an active server, interrupting playback; it does not start a stopped server. Theme/language changes are independent.
7. Overview provides health/logs, repair, updates and removal. Server updates appear only for newer upstream stable versions and require explicit confirmation. Catalogue refresh does not update server software. Removal keeps configuration/media and uses the trash for managed files.

The built-in Instructions menu contains the localized guide. See [known limitations](COMPATIBILITY.md) before interpreting a successful HTTP response as physical playback support.

## Distribution-specific installation and removal

DEB: install with APT and answer the English language question. ZIP: extract and run `./install.sh` as the desktop user; `--language en` is available for unattended use. Windows: run the EXE installer without administrator rights and select the first-launch language. Existing preferences are preserved; change language later from the Language menu.

Remove the managed UMS server from Overview first if its binaries are no longer needed. Remove the panel using APT on Debian-family systems, `~/.local/share/ums-control/uninstall.sh` for the ZIP installation, or Windows Settings → Apps. Panel removal preserves settings, profiles and media. The Windows/ZIP removal actions stop their managed server and disable its session autostart but keep server binaries.

On Windows, the server network selector lists only connected physical Ethernet/Wi-Fi adapters with a usable IPv4 address. Virtual, VPN, Bluetooth and disconnected adapters are excluded. A direct LAN does not require a default gateway or Internet access. A previously saved unavailable adapter remains explicitly marked as unavailable; it is never silently replaced.

### Device identity after a TV restart

Some TVs regenerate their UPnP UUID after a full power cycle. When that UUID has no saved profile, UMS Control reapplies the profile explicitly saved for the actual requesting IP before browsing. A configured UUID still has priority. Other clients do not inherit its shared folders; reserve the TV address in your router if necessary.
