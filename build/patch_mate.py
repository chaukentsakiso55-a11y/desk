from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()

def replace_once(path, old, new):
    p = root / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Expected block not found in {path}")
    if text.count(old) != 1:
        raise SystemExit(f"Expected exactly one match in {path}, found {text.count(old)}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")

replace_once(
    "app/pubspec.yaml",
    "version: 1.0.3+103\n",
    "version: 1.0.5+105\n",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''            "mate" -> "mate mate-terminal"
''',
    '''            "mate" -> "mate mate-terminal gvfs mate-applets"
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        env["PATH"] = listOf(
            "${prefixDir.absolutePath}/bin",
            "${prefixDir.absolutePath}/lib/xfce4/panel",
            System.getenv("PATH") ?: "/system/bin",
        ).joinToString(":")
''',
    '''        env["PATH"] = listOf(
            "${prefixDir.absolutePath}/bin",
            "${prefixDir.absolutePath}/libexec",
            "${prefixDir.absolutePath}/lib/xfce4/panel",
            System.getenv("PATH") ?: "/system/bin",
        ).joinToString(":")
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        env["XDG_DATA_DIRS"] = "${prefixDir.absolutePath}/share"
''',
    '''        env["XDG_DATA_DIRS"] = "${prefixDir.absolutePath}/share"
        env["GIO_EXTRA_MODULES"] = "${prefixDir.absolutePath}/lib/gio/modules"
        env["GVFS_DISABLE_FUSE"] = "1"
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''    /** Relocate commands that Xfce compiled as absolute Termux paths. */
    private fun patchEmbeddedXfcePaths() {
''',
    '''    /** Relocate commands that MATE/GLib compiled as absolute Termux paths. */
    private fun patchEmbeddedMatePaths() {
        val oldLauncher = "/data/data/com.termux/files/usr/libexec/gio-launch-desktop"
        val launcherName = "../usr/libexec/gio-launch-desktop"
        listOf(
            File(prefixDir, "lib"),
            File(prefixDir, "libexec"),
            File(prefixDir, "bin"),
        ).forEach { directory ->
            if (!directory.exists()) return@forEach
            directory.walkTopDown()
                .filter { file ->
                    file.isFile &&
                        file.canRead() &&
                        (
                            file.name.startsWith("libgio-2.0.so") ||
                            file.name.startsWith("libmate") ||
                            file.name.startsWith("caja") ||
                            file.name.startsWith("mate-")
                        )
                }
                .forEach { file ->
                    runCatching {
                        patchEmbeddedCommand(file, oldLauncher, launcherName)
                    }.onFailure { error ->
                        Log.w(TAG, "Could not relocate MATE command in ${file.name}: ${error.message}")
                    }
                }
        }
    }

    /** Relocate commands that Xfce compiled as absolute Termux paths. */
    private fun patchEmbeddedXfcePaths() {
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        patchShebangs()
        patchElfRunpaths(prefixDir)
        compileSocketHook()
        patchEmbeddedXfcePaths()

        val clipboardTool = File(binDir, "xclip")
''',
    '''        patchShebangs()
        patchElfRunpaths(prefixDir)
        compileSocketHook()
        patchEmbeddedXfcePaths()

        if (selectedDesktop == "mate") {
            val mateNeedsRepair =
                !isDpkgPackageInstalled("gvfs") ||
                !isDpkgPackageInstalled("mate-applets") ||
                !File(prefixDir, "libexec/gio-launch-desktop").canExecute()
            if (mateNeedsRepair) {
                Log.i(TAG, "Repairing MATE desktop compatibility packages")
                installPackageGroup("pkg install -y glib gvfs mate-applets mate-terminal")
                patchShebangs(force = true)
            }
            patchEmbeddedMatePaths()
        }

        val clipboardTool = File(binDir, "xclip")
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        compileSocketHook()
        patchEmbeddedXfcePaths()
        marker.writeText(selectedDesktop)
''',
    '''        compileSocketHook()
        patchEmbeddedXfcePaths()
        if (selectedDesktop == "mate") {
            patchShebangs(force = true)
            patchEmbeddedMatePaths()
        }
        marker.writeText(selectedDesktop)
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        val desktopCommand = when (selectedDesktop) {
            "lxqt" -> "startlxqt"
            "mate" -> "mate-session"
            "kde" -> "startplasma-x11"
''',
    '''        val desktopCommand = when (selectedDesktop) {
            "lxqt" -> "startlxqt"
            "mate" -> "mate-settings-daemon >/dev/null 2>&1 & marco --replace >/dev/null 2>&1 & caja --no-default-window >/dev/null 2>&1 & exec mate-panel"
            "kde" -> "startplasma-x11"
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        val processes = when (normalizedDesktop(desktopEnv)) {
            "lxqt" -> listOf("lxqt-session", "lxqt-panel")
            "mate" -> listOf("mate-session", "mate-panel")
            "kde" -> listOf("plasmashell")
''',
    '''        val processes = when (normalizedDesktop(desktopEnv)) {
            "lxqt" -> listOf("lxqt-session", "lxqt-panel")
            "mate" -> listOf("marco", "mate-panel")
            "kde" -> listOf("plasmashell")
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/view/DesktopActivity.kt",
    '''            desktopRevealed = true
            loadingMessageHandler.removeCallbacks(loadingMessageTicker)
            loadingMessageHandler.removeCallbacks(loadingEstimateTicker)
            if (!ready) Log.w(TAG, "Revealing desktop after readiness timeout")
            Log.i(TAG, "Desktop revealed ready=$ready")
''',
    '''            if (!ready) {
                loadingMessageHandler.removeCallbacks(loadingMessageTicker)
                loadingMessageHandler.removeCallbacks(loadingEstimateTicker)
                loadingStatus?.text = "Linux desktop failed to start"
                loadingEstimate?.text = "Returning to DroidDesk so you can retry"
                Log.e(TAG, "Desktop readiness timed out; refusing to reveal an empty X11 canvas")
                Toast.makeText(
                    this,
                    "Desktop failed to start. DroidDesk returned instead of showing a black screen.",
                    Toast.LENGTH_LONG,
                ).show()
                loadingMessageHandler.postDelayed({ finish() }, 1_800)
                return@runOnUiThread
            }
            desktopRevealed = true
            loadingMessageHandler.removeCallbacks(loadingMessageTicker)
            loadingMessageHandler.removeCallbacks(loadingEstimateTicker)
            Log.i(TAG, "Desktop revealed ready=true")
''',
)

print("Applied DroidDesk MATE compatibility fixes.")
