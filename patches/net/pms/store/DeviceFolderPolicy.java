/* SPDX-License-Identifier: GPL-2.0-only
 * UMS Control per-device folder policy. */
package net.pms.store;

import java.io.File;
import java.io.IOException;
import net.pms.renderers.Renderer;
import net.pms.renderers.devices.MediaScannerDevice;
import net.pms.store.container.TranscodeVirtualFolder;

public final class DeviceFolderPolicy {
    private DeviceFolderPolicy() { }

    public static boolean enabled(Renderer renderer) {
        return renderer != null && !(renderer instanceof MediaScannerDevice) && renderer.hasFolderPolicy();
    }

    private static boolean contains(Renderer renderer, File file, boolean convert) {
        if (file == null) return false;
        try {
            java.nio.file.Path path = file.getCanonicalFile().toPath();
            for (File root : renderer.getPolicyFolders(convert)) {
                if (path.startsWith(root.toPath())) return true;
            }
        } catch (IOException e) { return false; }
        return false;
    }

    public static boolean matches(File file, java.util.List<File> included, java.util.List<File> excluded) {
        if (file == null) return false;
        try {
            java.nio.file.Path path = file.getCanonicalFile().toPath();
            int depth = -1; boolean result = false;
            for (File root : included) {
                java.nio.file.Path candidate = root.toPath();
                if (path.startsWith(candidate) && candidate.getNameCount() > depth) {
                    depth = candidate.getNameCount(); result = true;
                }
            }
            for (File root : excluded) {
                java.nio.file.Path candidate = root.toPath();
                if (path.startsWith(candidate) && candidate.getNameCount() >= depth) {
                    depth = candidate.getNameCount(); result = false;
                }
            }
            return result;
        } catch (IOException e) { return false; }
    }

    public static boolean convert(Renderer renderer, StoreResource resource) {
        if (!enabled(renderer)) return true;
        return resource instanceof SystemFileResource file &&
            contains(renderer, file.getSystemFile(), false) && (renderer.isAutomaticDelivery() || matches(file.getSystemFile(), renderer.getPolicyFolders(true), renderer.getPolicyPaths("ums_control_convert_exclusions")));
    }

    /** Presentation only: keep source items available internally to build variants. */
    public static boolean grouped(Renderer renderer) {
        return enabled(renderer) && !renderer.getUmsConfiguration().isDisableTranscoding();
    }

    public static boolean visible(Renderer renderer, StoreResource resource) {
        if (!allowed(renderer, resource)) return false;
        return !(grouped(renderer) && resource instanceof StoreItem item &&
            item.getFormat() != null && item.getFormat().isVideo() && !item.isInsideTranscodeFolder());
    }

    public static boolean allowed(Renderer renderer, StoreResource resource) {
        if (resource == null) return false;
        if (!enabled(renderer)) return true;
        if (resource instanceof MediaStore) return true;
        if (resource instanceof TranscodeVirtualFolder && !renderer.getUmsConfiguration().isShowTranscodeFolder()) return false;
        if (resource instanceof SystemFileResource file) {
            if (resource instanceof TranscodeVirtualFolder && !grouped(renderer) && !convert(renderer, resource)) return false;
            return contains(renderer, file.getSystemFile(), false);
        }
        if (resource instanceof TranscodeVirtualFolder) {
            return resource.getParent() != null && (grouped(renderer) || convert(renderer, resource.getParent()));
        }
        // No global virtual library, external feed or temporary URL bypass.
        return false;
    }
}
