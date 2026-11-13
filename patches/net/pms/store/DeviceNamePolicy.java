/* SPDX-License-Identifier: GPL-2.0-only
 * Presentation-only video names. Never changes a file, codec or access rule. */
package net.pms.store;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.text.Normalizer;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import net.pms.renderers.Renderer;

public final class DeviceNamePolicy {
    private DeviceNamePolicy() { }
    private static final int MAX_STEM = 96;
    private record Names(long modified, long expires, Set<String> collisions) { }
    private static final Map<String, Names> CACHE = new LinkedHashMap<>(32, .75f, true) {
        @Override protected boolean removeEldestEntry(Map.Entry<String, Names> entry) { return size() > 128; }
    };

    public static boolean enabled(StoreResource resource) {
        if (!(resource instanceof StoreItem item) || !(resource instanceof SystemFileResource file) ||
            item.getMediaInfo() == null || !item.getMediaInfo().isVideo()) return false;
        Renderer renderer = resource.getDefaultRenderer();
        if (!DeviceFolderPolicy.enabled(renderer) || !DeviceFolderPolicy.allowed(renderer, resource)) return false;
        String mode = renderer.getNameDeliveryMode();
        return "compatible".equals(mode) || ("selected".equals(mode) && DeviceFolderPolicy.matches(
            file.getSystemFile(), renderer.getPolicyPaths("ums_control_name_folders"),
            renderer.getPolicyPaths("ums_control_name_exclusions")));
    }

    public static String clean(String value) {
        String normalized = Normalizer.normalize(value.toLowerCase(Locale.ROOT), Normalizer.Form.NFKD)
            .replace("ß", "ss").replace("æ", "ae").replace("œ", "oe").replace("ø", "o").replace("ł", "l");
        return normalized.replaceAll("[^a-z0-9]", "");
    }

    private static String stem(String value) {
        int dot = value.lastIndexOf('.');
        return dot > 0 ? value.substring(0, dot) : value;
    }

    private static String extension(String value) {
        int dot = value.lastIndexOf('.');
        return dot >= 0 ? clean(value.substring(dot + 1)).substring(0, Math.min(10, clean(value.substring(dot + 1)).length())) : "";
    }

    private static String hash(String value) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8))).substring(0, 12); }
        catch (java.security.NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }

    private static synchronized boolean collision(File file, String base) {
        File parent = file.getParentFile();
        if (parent == null) return false;
        String key = parent.getAbsolutePath(); long now = System.currentTimeMillis();
        Names names = CACHE.get(key);
        if (names == null || names.modified != parent.lastModified() || names.expires < now) {
            Set<String> seen = new HashSet<>(); Set<String> duplicates = new HashSet<>();
            String[] entries = parent.list();
            if (entries == null) return true; // Unreadable directory: use a stable suffix.
            for (String entry : entries) {
                String name = clean(stem(entry));
                if (!seen.add(name)) duplicates.add(name);
            }
            names = new Names(parent.lastModified(), now + 30000, duplicates); CACHE.put(key, names);
        }
        return names.collisions.contains(base);
    }

    public static String filename(StoreItem item) {
        File file = ((SystemFileResource) item).getSystemFile();
        String base = clean(stem(file.getName()));
        boolean suffix = base.isEmpty() || base.length() > MAX_STEM || collision(file, base);
        if (base.isEmpty()) base = "video";
        if (suffix) base = base.substring(0, Math.min(base.length(), MAX_STEM - 12)) + hash(file.getAbsolutePath());
        String ext = extension(file.getName());
        return base + (ext.isEmpty() ? "" : "." + ext);
    }

    public static String title(StoreResource resource, String oldTitle) {
        StoreItem item = (StoreItem) resource;
        String name = filename(item);
        if (resource.isInsideTranscodeFolder()) {
            // Keep the episode identifiable AND distinguish the audio/subtitle choices.
            String variant = clean(oldTitle);
            String base = stem(name) + variant;
            if (base.length() > MAX_STEM) base = base.substring(0, MAX_STEM - 12) + hash(base);
            String ext = extension(name);
            return base + (ext.isEmpty() ? "" : "." + ext);
        }
        return name;
    }

    public static String mediaURL(StoreItem item, String transcodedExtension) {
        String url = item.getMediaURL();
        if (transcodedExtension.isEmpty()) return url;
        // HLS has a route marker consumed by UMS, not just a cosmetic extension.
        if (transcodedExtension.endsWith(".m3u8")) return url + transcodedExtension;
        int slash = url.lastIndexOf('/'); int dot = url.lastIndexOf('.');
        String ext = extension(transcodedExtension);
        return (dot > slash ? url.substring(0, dot) : url) + "." + ext;
    }
}
