from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()

pubspec = root / "app/pubspec.yaml"
text = pubspec.read_text(encoding="utf-8")
if "version: 2.0.4+204" not in text:
    raise SystemExit("Expected v2.0.4 before v2.0.5")
text = text.replace("version: 2.0.4+204", "version: 2.0.5+205", 1)
asset_marker = "    - assets/ember/ember_server.py\n"
assets = (
    "    - assets/ember/ember_server.py\n"
    "    - assets/ember/ember-native.zip\n"
    "    - assets/desktop/droiddesk_files.py\n"
    "    - assets/desktop/import_center.py\n"
)
if "assets/ember/ember-native.zip" not in text:
    if asset_marker not in text:
        raise SystemExit("Pubspec asset marker missing")
    text = text.replace(asset_marker, assets, 1)
pubspec.write_text(text, encoding="utf-8")

runtime = root / "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt"
text = runtime.read_text(encoding="utf-8")

old_path = '''        env["PATH"] = listOf(
            "${prefixDir.absolutePath}/bin",
            "${prefixDir.absolutePath}/libexec",
            "${prefixDir.absolutePath}/lib/xfce4/panel",
            System.getenv("PATH") ?: "/system/bin",
        ).joinToString(":")
'''
new_path = '''        env["PATH"] = listOf(
            "${File(homeDir, ".local/bin").absolutePath}",
            "${prefixDir.absolutePath}/bin",
            "${prefixDir.absolutePath}/libexec",
            "${prefixDir.absolutePath}/lib/xfce4/panel",
            System.getenv("PATH") ?: "/system/bin",
        ).joinToString(":")
'''
if old_path not in text:
    raise SystemExit("PATH block changed")
text = text.replace(old_path, new_path, 1)

helpers = r'''
    private fun copyFlutterAsset(assetPath: String, target: File): Boolean = runCatching {
        target.parentFile?.mkdirs()
        context.assets.open("flutter_assets/$assetPath").use { input ->
            target.outputStream().use { output -> input.copyTo(output) }
        }
        true
    }.onFailure { Log.w(TAG, "Could not copy asset $assetPath", it) }.getOrDefault(false)

    private fun extractV205Zip(zipFile: File, targetDir: File): Boolean = runCatching {
        targetDir.mkdirs()
        val base = targetDir.canonicalFile
        java.util.zip.ZipInputStream(zipFile.inputStream().buffered()).use { zip ->
            var entry = zip.nextEntry
            while (entry != null) {
                val out = File(targetDir, entry.name).canonicalFile
                require(out == base || out.path.startsWith(base.path + File.separator)) {
                    "Unsafe archive entry: ${entry.name}"
                }
                if (entry.isDirectory) {
                    out.mkdirs()
                } else {
                    out.parentFile?.mkdirs()
                    out.outputStream().use { stream -> zip.copyTo(stream) }
                }
                zip.closeEntry()
                entry = zip.nextEntry
            }
        }
        true
    }.onFailure { Log.w(TAG, "Could not extract archive ${zipFile.name}", it) }.getOrDefault(false)

    private fun installV205Launchers() {
        val localBin = File(homeDir, ".local/bin").apply { mkdirs() }
        val localApps = File(homeDir, ".local/share/applications").apply { mkdirs() }
        val desktopDir = File(homeDir, "Desktop").apply { mkdirs() }
        val toolsDir = File(homeDir, ".local/share/droiddesk-tools").apply { mkdirs() }
        val cacheDir = File(homeDir, ".cache/droiddesk").apply { mkdirs() }

        val filesApp = File(toolsDir, "droiddesk_files.py")
        val importApp = File(toolsDir, "import_center.py")
        copyFlutterAsset("assets/desktop/droiddesk_files.py", filesApp)
        copyFlutterAsset("assets/desktop/import_center.py", importApp)

        val emberRoot = File(homeDir, ".local/share/ember-native")
        val emberMarker = File(emberRoot, ".droiddesk-v205")
        if (!emberMarker.exists()) {
            val archive = File(cacheDir, "ember-native.zip")
            if (copyFlutterAsset("assets/ember/ember-native.zip", archive)) {
                emberRoot.deleteRecursively()
                if (extractV205Zip(archive, emberRoot)) {
                    emberMarker.parentFile?.mkdirs()
                    emberMarker.writeText("v2.0.5")
                }
                archive.delete()
            }
        }

        fun shell(name: String, body: String): File {
            val file = File(localBin, name)
            file.writeText("#!${File(binDir, "bash").absolutePath}\nset -u\n$body\n")
            file.setExecutable(true, false)
            return file
        }

        val supportLog = File(cacheDir, "support-install.log").absolutePath
        val filesLauncher = shell(
            "droiddesk-files",
            """
            if ! "${File(binDir, "python3").absolutePath}" -c 'import PyQt6' >/dev/null 2>&1; then
              "${File(binDir, "pkg").absolutePath}" install -y pyqt6 >>"$supportLog" 2>&1 || exit 1
            fi
            exec "${File(binDir, "python3").absolutePath}" "${filesApp.absolutePath}" "${'$'}@"
            """.trimIndent(),
        )
        val importLauncher = shell(
            "droiddesk-import",
            """
            if ! "${File(binDir, "python3").absolutePath}" -c 'import PyQt6' >/dev/null 2>&1; then
              "${File(binDir, "pkg").absolutePath}" install -y pyqt6 >>"$supportLog" 2>&1 || exit 1
            fi
            exec "${File(binDir, "python3").absolutePath}" "${importApp.absolutePath}"
            """.trimIndent(),
        )
        val emberLauncher = shell(
            "ember",
            """
            needed=""
            "${File(binDir, "python3").absolutePath}" -c 'import PyQt6' >/dev/null 2>&1 || needed="${'$'}needed pyqt6"
            "${File(binDir, "python3").absolutePath}" -c 'import numpy' >/dev/null 2>&1 || needed="${'$'}needed python-numpy"
            "${File(binDir, "python3").absolutePath}" -c 'import psutil' >/dev/null 2>&1 || needed="${'$'}needed python-psutil"
            if [ -n "${'$'}needed" ]; then
              "${File(binDir, "pkg").absolutePath}" install -y ${'$'}needed >>"$supportLog" 2>&1 || exit 1
            fi
            export DISPLAY="${'$'}{DISPLAY:-:0}"
            export GDK_BACKEND=x11
            export QT_QPA_PLATFORM=xcb
            export EMBER_DATA_DIR="${File(homeDir, ".config/ember").absolutePath}"
            export PYTHONPATH="${emberRoot.absolutePath}:${emberRoot.absolutePath}/vendor:${'$'}{PYTHONPATH:-}"
            cd "${emberRoot.absolutePath}"
            exec "${File(binDir, "python3").absolutePath}" main.py
            """.trimIndent(),
        )
        val firefoxLauncher = shell(
            "firefox-droiddesk",
            """
            export DISPLAY="${'$'}{DISPLAY:-:0}"
            export GDK_BACKEND=x11
            export MOZ_ENABLE_WAYLAND=0
            export MOZ_DBUS_REMOTE=0
            profile="${File(homeDir, ".mozilla/droiddesk").absolutePath}"
            mkdir -p "${'$'}profile"
            exec "${File(binDir, "firefox").absolutePath}" --no-remote --profile "${'$'}profile" "${'$'}@"
            """.trimIndent(),
        )
        val vlcLauncher = shell(
            "vlc-droiddesk",
            """
            if [ ! -x "${File(binDir, "vlc").absolutePath}" ]; then
              "${File(binDir, "pkg").absolutePath}" install -y vlc-qt >>"$supportLog" 2>&1 || exit 1
            fi
            export DISPLAY="${'$'}{DISPLAY:-:0}"
            export QT_QPA_PLATFORM=xcb
            exec "${File(binDir, "vlc").absolutePath}" "${'$'}@"
            """.trimIndent(),
        )

        fun intercept(real: File, name: String) {
            if (!real.exists()) return
            shell(
                name,
                """
                for arg in "${'$'}@"; do
                  case "${'$'}arg" in
                    computer:*|trash:*|file:///|/) exec "${filesLauncher.absolutePath}" "${'$'}arg" ;;
                  esac
                done
                exec "${real.absolutePath}" "${'$'}@"
                """.trimIndent(),
            )
        }
        intercept(File(binDir, "caja"), "caja")
        intercept(File(binDir, "thunar"), "thunar")

        fun desktop(
            file: File,
            name: String,
            comment: String,
            exec: String,
            icon: String,
            categories: String,
            mime: String = "",
        ) {
            file.parentFile?.mkdirs()
            file.writeText(
                """
                [Desktop Entry]
                Version=1.0
                Type=Application
                Name=$name
                Comment=$comment
                Exec=$exec
                Icon=$icon
                Terminal=false
                Categories=$categories
                ${if (mime.isBlank()) "" else "MimeType=$mime"}
                StartupNotify=true
                """.trimIndent() + "\n",
            )
            file.setExecutable(true, false)
        }

        desktop(
            File(localApps, "droiddesk-files.desktop"),
            "DroidDesk Files",
            "Linux and phone storage",
            "${filesLauncher.absolutePath} %U",
            "system-file-manager",
            "Utility;FileManager;",
        )
        desktop(
            File(localApps, "droiddesk-ember.desktop"),
            "Ember",
            "Native Ember neural command node",
            emberLauncher.absolutePath,
            "applications-development",
            "Utility;Development;Network;",
        )
        desktop(
            File(localApps, "droiddesk-import.desktop"),
            "Import Apps",
            "Import Linux packages, scripts, source folders and APKs",
            importLauncher.absolutePath,
            "document-open",
            "Utility;Development;",
        )
        desktop(
            File(localApps, "firefox.desktop"),
            "Firefox",
            "Firefox for the DroidDesk X11 session",
            "${firefoxLauncher.absolutePath} %u",
            "firefox",
            "Network;WebBrowser;",
            "text/html;x-scheme-handler/http;x-scheme-handler/https;",
        )
        desktop(
            File(localApps, "vlc-droiddesk.desktop"),
            "VLC Media Player",
            "Play video and audio in Linux",
            "${vlcLauncher.absolutePath} %U",
            "vlc",
            "AudioVideo;Player;",
            "video/mp4;video/x-matroska;video/webm;video/quicktime;audio/mpeg;audio/flac;audio/ogg;audio/x-wav;",
        )

        listOf(
            "Computer" to "${filesLauncher.absolutePath} ${homeDir.absolutePath}",
            "Phone Storage" to "${filesLauncher.absolutePath} /storage/emulated/0",
            "Downloads" to "${filesLauncher.absolutePath} /storage/emulated/0/Download",
            "Camera" to "${filesLauncher.absolutePath} /storage/emulated/0/DCIM/Camera",
            "Pictures" to "${filesLauncher.absolutePath} /storage/emulated/0/Pictures",
            "Movies" to "${filesLauncher.absolutePath} /storage/emulated/0/Movies",
            "Music" to "${filesLauncher.absolutePath} /storage/emulated/0/Music",
            "Documents" to "${filesLauncher.absolutePath} /storage/emulated/0/Documents",
            "Import Apps" to importLauncher.absolutePath,
        ).forEach { (name, command) ->
            val safe = name.replace(" ", "-")
            desktop(
                File(desktopDir, "DroidDesk-$safe.desktop"),
                name,
                "DroidDesk $name",
                command,
                if (name == "Import Apps") "document-open" else "folder",
                "Utility;FileManager;",
            )
        }

        File(localApps, "droiddesk-python.desktop").takeIf(File::exists)?.copyTo(
            File(desktopDir, "DroidDesk-Python.desktop"),
            overwrite = true,
        )?.setExecutable(true, false)
        File(localApps, "droiddesk-ember.desktop").copyTo(
            File(desktopDir, "DroidDesk-Ember.desktop"),
            overwrite = true,
        ).setExecutable(true, false)

        val phoneLink = File(homeDir, "Phone Storage")
        executeCommand(
            "rm -f '${phoneLink.absolutePath}' >/dev/null 2>&1 || true; " +
                "ln -s /storage/emulated/0 '${phoneLink.absolutePath}' >/dev/null 2>&1 || true",
        )

        val gtkBookmarks = File(homeDir, ".config/gtk-3.0/bookmarks")
        gtkBookmarks.parentFile?.mkdirs()
        gtkBookmarks.writeText(
            """
            file://${homeDir.absolutePath} Linux Home
            file:///storage/emulated/0 Phone Storage
            file:///storage/emulated/0/Download Downloads
            file:///storage/emulated/0/DCIM/Camera Camera
            file:///storage/emulated/0/Pictures Pictures
            file:///storage/emulated/0/Movies Movies
            file:///storage/emulated/0/Music Music
            file:///storage/emulated/0/Documents Documents
            """.trimIndent() + "\n",
        )

        executeCommand(
            "xdg-mime default droiddesk-files.desktop inode/directory >/dev/null 2>&1 || true; " +
                "xdg-mime default firefox.desktop x-scheme-handler/http >/dev/null 2>&1 || true; " +
                "xdg-mime default firefox.desktop x-scheme-handler/https >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop video/mp4 >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop video/x-matroska >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop video/webm >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop audio/mpeg >/dev/null 2>&1 || true",
        )
    }

    private fun prepareV205Support() {
        val marker = File(prefixDir, ".droiddesk_v205_support")
        if (marker.exists()) {
            installV205Launchers()
            return
        }
        val packages = listOf("pyqt6", "python-numpy", "python-psutil", "vlc-qt", "xdg-utils")
        val missing = packages.filterNot(::isDpkgPackageInstalled)
        if (missing.isNotEmpty()) {
            val packageList = missing.joinToString(" ")
            if (!installPackageGroup("pkg install -y $packageList")) {
                Log.w(TAG, "Some v2.0.5 desktop integration packages could not be installed")
                installV205Launchers()
                return
            }
        }
        installV205Launchers()
        marker.writeText("ready")
    }

'''
marker = "    private fun refreshDesktopMenus() {\n"
if marker not in text:
    raise SystemExit("refreshDesktopMenus marker missing")
text = text.replace(marker, helpers + marker, 1)

old_refresh = '''    private fun refreshDesktopMenus() {
        installDroidDeskBuiltIns()
        syncStoreDesktopLaunchers()
'''
new_refresh = '''    private fun refreshDesktopMenus() {
        installDroidDeskBuiltIns()
        installV205Launchers()
        syncStoreDesktopLaunchers()
'''
if old_refresh not in text:
    raise SystemExit("v2.0.3 refreshDesktopMenus block changed")
text = text.replace(old_refresh, new_refresh, 1)

old_finish = '''        marker.writeText(selectedDesktop)
        refreshDesktopMenus()
        onProgress?.invoke(1.0, "Native Linux setup complete")
'''
new_finish = '''        prepareV205Support()
        marker.writeText(selectedDesktop)
        refreshDesktopMenus()
        onProgress?.invoke(1.0, "Native Linux setup complete")
'''
if old_finish not in text:
    raise SystemExit("setup finish block changed")
text = text.replace(old_finish, new_finish, 1)

runtime.write_text(text, encoding="utf-8")

catalog = root / "app/lib/screens/apps/app_catalog_screen.dart"
text = catalog.read_text(encoding="utf-8")
text = text.replace("      'vlc',\n      'VLC',", "      'vlc-qt',\n      'VLC',", 1)
catalog.write_text(text, encoding="utf-8")

print("Applied v2.0.5 native desktop integration.")
