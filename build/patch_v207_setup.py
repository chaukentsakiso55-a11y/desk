from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()

pubspec = root / "app/pubspec.yaml"
text = pubspec.read_text(encoding="utf-8")
if "version: 2.0.6+206" not in text:
    raise SystemExit("Expected v2.0.6 before v2.0.7")
pubspec.write_text(
    text.replace("version: 2.0.6+206", "version: 2.0.7+207", 1),
    encoding="utf-8",
)

runtime = root / "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt"
text = runtime.read_text(encoding="utf-8")

helpers = r'''
    private fun repairDpkgState(): Boolean {
        repeat(3) { attempt ->
            patchShebangs(force = true)
            executeCommand(
                "timeout --signal=TERM --kill-after=5s 180s " +
                    "env DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=5 " +
                    "-o Dpkg::Options::=--force-confdef " +
                    "-o Dpkg::Options::=--force-confold --fix-broken install -y",
            )
            patchShebangs(force = true)
            val configure = executeCommand(
                "timeout --signal=TERM --kill-after=5s 180s dpkg --configure -a",
            )
            if (!configure.startsWith("Error:")) return true
            Log.w(TAG, "dpkg repair attempt ${attempt + 1} did not finish cleanly")
        }
        return false
    }

    private fun installPackagesResilient(
        packages: List<String>,
        label: String,
        onProgress: ((Double, String) -> Unit)? = null,
        progress: Double = 0.5,
    ): Boolean {
        var missing = packages.filterNot(::isDpkgPackageInstalled)
        if (missing.isEmpty()) {
            onProgress?.invoke(progress, "$label already installed")
            return true
        }

        repeat(3) { attempt ->
            if (packageOperationCancelled) return false
            onProgress?.invoke(
                progress,
                if (attempt == 0) label else "$label — retry ${attempt + 1}/3",
            )

            val packageNames = missing.joinToString(" ")
            executeCommand(
                "env DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=5 " +
                    "-o Dpkg::Options::=--force-confdef " +
                    "-o Dpkg::Options::=--force-confold install -y $packageNames",
            )
            if (packageOperationCancelled) return false

            repairDpkgState()
            missing = packages.filterNot(::isDpkgPackageInstalled)
            if (missing.isEmpty()) return true

            if (attempt < 2) {
                refreshCorePackageLists(null)
            }
        }

        Log.e(TAG, "Packages still missing after retries: ${missing.joinToString(" ")}")
        return false
    }

    private fun desktopCoreReady(desktop: String): Boolean {
        val required = when (desktop) {
            "mate" -> listOf("mate-session", "mate-panel", "marco", "mate-terminal")
            "lxqt" -> listOf("startlxqt", "lxqt-panel", "qterminal")
            "kde" -> listOf("startplasma-x11", "plasmashell", "konsole")
            else -> listOf("startxfce4", "xfce4-panel", "xfdesktop", "xfce4-terminal")
        }
        return required.all { File(binDir, it).canExecute() }
    }

'''
marker = "    private fun installPackageGroup"
if marker not in text:
    raise SystemExit("installPackageGroup marker missing")
text = text.replace(marker, helpers + marker, 1)

old = '''        if (!installPackageGroup("dpkg --configure -a")) {
            Log.e(TAG, "Initial dpkg --configure -a failed")
            return false
        }
'''
new = '''        if (!repairDpkgState()) {
            onProgress?.invoke(-1.0, "Package database repair failed. Retry will resume from cached packages.")
            Log.e(TAG, "Initial dpkg recovery failed")
            return false
        }
'''
if old not in text:
    raise SystemExit("Initial package recovery block changed")
text = text.replace(old, new, 1)

old = '''        if (!installPackageGroup("pkg install -y xorg-xrandr pulseaudio xclip xkeyboard-config")) {
            Log.e(TAG, "Native X11 runtime package install failed")
            return false
        }
'''
new = '''        if (!installPackagesResilient(
                listOf("xorg-xrandr", "pulseaudio", "xclip", "xkeyboard-config"),
                "Installing X11 and audio packages...",
                onProgress,
                0.34,
            )) {
            onProgress?.invoke(-1.0, "X11/audio packages could not be repaired. Retry will resume from cached downloads.")
            Log.e(TAG, "Native X11 runtime package install failed")
            return false
        }
'''
if old not in text:
    raise SystemExit("X11 package block changed")
text = text.replace(old, new, 1)

old = '''        if (!installPackageGroup("pkg install -y $desktopPackages")) {
            Log.e(TAG, "$selectedDesktop package install failed")
            return false
        }
'''
new = '''        val desktopPackageList = desktopPackages.split(" ").filter(String::isNotBlank)
        val desktopPackagesOk = installPackagesResilient(
            desktopPackageList,
            "Installing $selectedDesktop desktop packages...",
            onProgress,
            0.46,
        )
        if (!desktopPackagesOk && !desktopCoreReady(selectedDesktop)) {
            onProgress?.invoke(
                -1.0,
                "$selectedDesktop setup paused before the core desktop was ready. Tap Retry to resume without redownloading completed packages.",
            )
            Log.e(TAG, "$selectedDesktop package install failed and core desktop is incomplete")
            return false
        }
        if (!desktopPackagesOk) {
            Log.w(TAG, "$selectedDesktop meta-package was not fully configured, but core desktop binaries are ready")
            onProgress?.invoke(0.68, "$selectedDesktop core recovered; continuing setup")
        }
'''
if old not in text:
    raise SystemExit("Desktop package block changed")
text = text.replace(old, new, 1)

old = '''        if (!installPackageGroup("pkg install -y $nativeTools")) {
            Log.e(TAG, "Native Termux utility package install failed")
            return false
        }
'''
new = '''        if (!installPackagesResilient(
                nativeTools.split(" "),
                "Installing Desktop Essentials tools...",
                onProgress,
                0.84,
            )) {
            Log.w(TAG, "Some optional command-line tools are still missing; desktop setup will continue")
            onProgress?.invoke(0.92, "Desktop is ready; optional tools can finish later from Apps")
        }
'''
if old not in text:
    raise SystemExit("Native tools block changed")
text = text.replace(old, new, 1)

runtime.write_text(text, encoding="utf-8")

main = root / "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/MainActivity.kt"
text = main.read_text(encoding="utf-8")

old = '''                "installDesktopNative" -> {
                    val desktopEnv = call.argument<String>("de") ?: "xfce4"
                    thread {
'''
new = '''                "installDesktopNative" -> {
                    val desktopEnv = call.argument<String>("de") ?: "xfce4"
                    startForegroundService("Installing Linux packages in background")
                    thread {
'''
if old not in text:
    raise SystemExit("installDesktopNative handler changed")
text = text.replace(old, new, 1)

old = '''                            ) { progress, status ->
                                runOnUiThread {
                                    MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).invokeMethod(
                                        "onInstallProgress",
                                        mapOf("progress" to progress, "status" to status),
                                    )
                                }
                            }
                            runOnUiThread { result.success(ok) }
'''
new = '''                            ) { progress, status ->
                                runOnUiThread {
                                    startForegroundService(status)
                                    MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).invokeMethod(
                                        "onInstallProgress",
                                        mapOf("progress" to progress, "status" to status),
                                    )
                                }
                            }
                            runOnUiThread {
                                startForegroundService(
                                    if (ok) "Linux setup complete" else "Linux setup paused — tap to retry",
                                )
                                result.success(ok)
                            }
'''
if old not in text:
    raise SystemExit("installDesktopNative progress block changed")
text = text.replace(old, new, 1)

old = '''    private fun startForegroundService() {
        val intent = Intent(this, DroidDeskService::class.java)
'''
new = '''    private fun startForegroundService(status: String = "Linux desktop is running") {
        val intent = Intent(this, DroidDeskService::class.java).apply {
            putExtra("status", status)
        }
'''
if old not in text:
    raise SystemExit("Foreground service helper changed")
text = text.replace(old, new, 1)

main.write_text(text, encoding="utf-8")

service = root / "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/service/DroidDeskService.kt"
text = service.read_text(encoding="utf-8")
old = '''    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = buildNotification("Linux desktop is running")
'''
new = '''    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val status = intent?.getStringExtra("status")
            ?.takeIf { it.isNotBlank() }
            ?: "Linux desktop is running"
        val notification = buildNotification(status)
'''
if old not in text:
    raise SystemExit("DroidDeskService onStartCommand changed")
text = text.replace(old, new, 1)
text = text.replace(
    'description = "Keeps the Linux desktop environment running"',
    'description = "Keeps Linux setup, downloads, and desktop sessions running"',
    1,
)
service.write_text(text, encoding="utf-8")

state = root / "app/lib/state/app_state.dart"
text = state.read_text(encoding="utf-8")
old = "throw StateError('Native Termux package installation failed');"
new = "throw StateError('Native Linux setup paused. Tap Retry to resume from downloaded packages.');"
if text.count(old) < 1:
    raise SystemExit("Native setup error message changed")
text = text.replace(old, new)
state.write_text(text, encoding="utf-8")

print("Applied v2.0.7 resumable background setup fixes.")
