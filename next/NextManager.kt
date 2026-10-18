package com.orailnoor.droiddesk.runtime

import android.app.ActivityManager
import android.content.Context
import android.hardware.display.DisplayManager
import android.os.Build
import android.os.Environment
import android.os.StatFs
import android.provider.Settings
import android.util.Log
import java.io.File
import java.net.NetworkInterface
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class NextManager(
    private val context: Context,
    private val runtime: LinuxRuntime,
    private val desktopIntegration: DesktopIntegration,
) {
    companion object {
        private const val TAG = "DroidDeskNext"
        private const val PREFS = "droiddesk_next"
    }

    private val prefs get() = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val home get() = File(context.filesDir, "home")
    private val prefix get() = File(context.filesDir, "usr")
    private val logFile get() = File(context.filesDir, "next/guardian.log")

    init {
        File(context.filesDir, "next").mkdirs()
        ensureOfflineRepairKit()
        ensureNotificationBridgeScripts()
        writePerformanceProfile(
            prefs.getString("performance_mode", "balanced") ?: "balanced",
            prefs.getInt("memory_limit_mb", 2048),
        )
    }

    fun status(): Map<String, Any> {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val memoryInfo = ActivityManager.MemoryInfo().also(am::getMemoryInfo)
        val stat = StatFs(context.filesDir.absolutePath)
        val displayManager = context.getSystemService(Context.DISPLAY_SERVICE) as DisplayManager
        val notificationAccess = Settings.Secure.getString(
            context.contentResolver,
            "enabled_notification_listeners",
        )?.contains(context.packageName) == true
        return mapOf(
            "performanceMode" to (prefs.getString("performance_mode", "balanced") ?: "balanced"),
            "memoryLimitMB" to prefs.getInt("memory_limit_mb", 2048),
            "totalRamMB" to memoryInfo.totalMem / (1024L * 1024L),
            "availableRamMB" to memoryInfo.availMem / (1024L * 1024L),
            "storageFreeMB" to stat.availableBytes / (1024L * 1024L),
            "linuxSizeMB" to directorySize(prefix) / (1024L * 1024L),
            "homeSizeMB" to directorySize(home) / (1024L * 1024L),
            "externalDisplays" to (displayManager.displays.size - 1).coerceAtLeast(0),
            "graphicsMode" to runtime.getGraphicsMode(),
            "installedDE" to runtime.getInstalledDE(),
            "running" to runtime.isRunning(),
            "sshRunning" to processRunning("sshd"),
            "vncRunning" to (processRunning("Xtigervnc") || processRunning("Xvnc")),
            "sharedFolders" to sharedFoldersReady(),
            "allFilesAccess" to if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) Environment.isExternalStorageManager() else true,
            "notificationAccess" to notificationAccess,
            "notificationBridge" to File(home, ".local/bin/droiddesk-notify-android.py").canExecute(),
            "audioBridge" to File(prefix, "bin/pulseaudio").canExecute(),
            "clipboardBridge" to File(prefix, "bin/xclip").canExecute(),
            "cameraBridge" to File(home, "Android/Camera").exists(),
            "localIp" to localIpv4(),
            "snapshotCount" to desktopIntegration.listSnapshots().size,
            "distros" to distroStatus(),
        )
    }

    fun guardianReport(): Map<String, Any> {
        val de = runtime.getInstalledDE().ifEmpty { "xfce4" }
        val desktopChecks = when (de) {
            "mate" -> listOf("bin/mate-panel", "bin/marco")
            "lxqt" -> listOf("bin/lxqt-session", "bin/lxqt-panel")
            "kde" -> listOf("bin/plasmashell")
            else -> listOf("bin/xfce4-panel", "bin/xfdesktop")
        }
        val checks = mutableListOf<Map<String, Any>>()
        fun add(id: String, label: String, ok: Boolean, detail: String) {
            checks += mapOf("id" to id, "label" to label, "ok" to ok, "detail" to detail)
        }
        add("bootstrap", "Linux bootstrap", runtime.isBootstrapped(), prefix.absolutePath)
        add("xkb", "X11 keyboard data", listOf(File(prefix, "share/X11/xkb"), File(prefix, "share/xkeyboard-config-2")).any(File::isDirectory), "Embedded X11 keyboard configuration")
        add("dbus", "D-Bus", File(prefix, "bin/dbus-daemon").canExecute(), "Desktop session bus")
        add("clipboard", "Clipboard bridge", File(prefix, "bin/xclip").canExecute(), "Android ↔ Linux text clipboard")
        add("audio", "Audio bridge", File(prefix, "bin/pulseaudio").canExecute(), "Phone audio transport")
        add("desktop", "Desktop shell", desktopChecks.all { File(prefix, it).exists() }, "$de · $desktopChecks")
        add("gio", "GLib launcher", File(prefix, "libexec/gio-launch-desktop").canExecute(), "Desktop menu launcher")
        val freeMb = StatFs(context.filesDir.absolutePath).availableBytes / (1024L * 1024L)
        add("storage", "Free storage", freeMb > 1024, "$freeMb MB free")
        add("home", "Linux home", home.exists() && home.canWrite(), home.absolutePath)
        add("graphics", "Graphics backend", true, runtime.getGraphicsMode())
        add("shared", "Android shared folders", sharedFoldersReady(), "Downloads · Documents · Pictures · Camera · Projects")
        add("notifications", "Notification bridge", File(home, ".local/bin/droiddesk-notify-android.py").canExecute(), "Linux ↔ Android notifications")
        val passed = checks.count { it["ok"] == true }
        val score = if (checks.isEmpty()) 0 else passed * 100 / checks.size
        appendLog("Guardian scan: $score% ($passed/${checks.size})")
        return mapOf("score" to score, "healthy" to (score >= 90), "checks" to checks, "timestamp" to System.currentTimeMillis())
    }

    fun repair(): Map<String, Any> {
        appendLog("Repair started")
        runtime.extractBootstrapIfNeeded(context)
        val de = runtime.getInstalledDE().ifEmpty { "xfce4" }
        val ok = runtime.installDesktopEnvironmentNative(de) { _, status -> appendLog(status) }
        runtime.executeCommand("pkg install -y xclip xkeyboard-config pulseaudio dbus libnotify openssh || true")
        configureSharedFolders()
        ensureOfflineRepairKit()
        ensureNotificationBridgeScripts()
        appendLog("Repair finished success=$ok")
        return guardianReport() + mapOf("repairCompleted" to ok)
    }

    fun setPerformanceMode(mode: String, memoryLimitMB: Int): Boolean {
        val safeMode = when (mode.lowercase()) {
            "battery", "balanced", "performance" -> mode.lowercase()
            else -> "balanced"
        }
        val safeLimit = memoryLimitMB.coerceIn(768, 8192)
        prefs.edit().putString("performance_mode", safeMode).putInt("memory_limit_mb", safeLimit).apply()
        writePerformanceProfile(safeMode, safeLimit)
        appendLog("Performance mode=$safeMode memory=${safeLimit}MB")
        return true
    }

    private fun writePerformanceProfile(mode: String, memoryLimitMB: Int) {
        val dir = File(home, ".config/droiddesk").apply { mkdirs() }
        val cpuThreads = Runtime.getRuntime().availableProcessors().coerceAtLeast(1)
        val threads = when (mode) { "battery" -> 2; "performance" -> cpuThreads; else -> cpuThreads.coerceAtMost(4) }
        val latency = when (mode) { "battery" -> 120; "performance" -> 40; else -> 70 }
        File(dir, "session-profile.sh").writeText(
            "export DROIDDESK_PERFORMANCE_MODE=$mode\n" +
            "export OMP_NUM_THREADS=$threads\n" +
            "export PULSE_LATENCY_MSEC=$latency\n" +
            "ulimit -v ${memoryLimitMB * 1024} 2>/dev/null || true\n"
        )
    }

    fun configureSharedFolders(): Map<String, Any> {
        val root = File(home, "Android").apply { mkdirs() }
        val storage = Environment.getExternalStorageDirectory()
        val targets = linkedMapOf(
            "Downloads" to File(storage, "Download"),
            "Documents" to File(storage, "Documents"),
            "Pictures" to File(storage, "Pictures"),
            "Camera" to File(storage, "DCIM/Camera"),
            "Projects" to File(storage, "Documents/DroidDeskProjects"),
        )
        val results = mutableMapOf<String, Boolean>()
        targets.forEach { (name, target) ->
            target.mkdirs()
            val link = File(root, name)
            runCatching {
                if (link.exists() || runCatching { android.system.Os.readlink(link.absolutePath) }.isSuccess) link.delete()
                android.system.Os.symlink(target.absolutePath, link.absolutePath)
                results[name] = true
            }.onFailure { results[name] = false }
        }
        appendLog("Shared folders: $results")
        return mapOf("ok" to results.values.all { it }, "folders" to results)
    }

    private fun sharedFoldersReady(): Boolean {
        val root = File(home, "Android")
        return listOf("Downloads", "Documents", "Pictures", "Camera", "Projects").all { name ->
            val f = File(root, name)
            f.exists() || runCatching { android.system.Os.readlink(f.absolutePath) }.isSuccess
        }
    }

    fun cleanCaches(): Map<String, Any> {
        val targets = listOf(
            File(prefix, "var/cache/apt/archives"),
            File(prefix, "var/lib/proot-distro/dlcache"),
            File(prefix, "var/lib/proot-distro/cache"),
            File(home, ".cache/thumbnails"),
        )
        val before = targets.sumOf(::directorySize)
        targets.forEach { t -> t.listFiles()?.forEach { it.deleteRecursively() } }
        val freed = (before - targets.sumOf(::directorySize)).coerceAtLeast(0)
        appendLog("Cache cleanup freed ${freed / (1024L * 1024L)} MB")
        return mapOf("freedBytes" to freed, "freedMB" to freed / (1024L * 1024L))
    }

    fun toggleSsh(enable: Boolean): Map<String, Any> {
        if (!enable) {
            runtime.executeCommand("pkill -x sshd >/dev/null 2>&1 || true")
            return mapOf("running" to false, "port" to 8022, "ip" to localIpv4())
        }
        runtime.executeCommand("pkg install -y openssh")
        runtime.executeCommand("ssh-keygen -A >/dev/null 2>&1 || true; pkill -x sshd >/dev/null 2>&1 || true; sshd -p 8022")
        val running = processRunning("sshd")
        appendLog("SSH started=$running")
        return mapOf("running" to running, "port" to 8022, "ip" to localIpv4())
    }

    fun toggleVnc(enable: Boolean, width: Int = 1280, height: Int = 720): Map<String, Any> {
        if (!enable) {
            runtime.executeCommand("vncserver -kill :1 >/dev/null 2>&1 || pkill -x Xtigervnc >/dev/null 2>&1 || true")
            return mapOf("running" to false, "address" to "127.0.0.1:5901")
        }
        runtime.executeCommand("pkg install -y tigervnc xfce4")
        val vncDir = File(home, ".vnc").apply { mkdirs() }
        File(vncDir, "xstartup").apply {
            writeText("#!${File(prefix, "bin/bash").absolutePath}\nexport DISPLAY=:1\nexec xfce4-session\n")
            setExecutable(true, false)
        }
        runtime.executeCommand("vncserver -kill :1 >/dev/null 2>&1 || true; vncserver :1 -localhost yes -geometry ${width.coerceIn(800, 2560)}x${height.coerceIn(480, 1600)} -SecurityTypes None")
        val running = processRunning("Xtigervnc") || processRunning("Xvnc")
        appendLog("VNC fallback started=$running")
        return mapOf("running" to running, "address" to "127.0.0.1:5901")
    }

    fun installDevPack(): Boolean {
        createRecoveryPoint()
        val output = runtime.executeCommand("for p in git python nodejs clang cmake make openjdk-17 openssh; do pkg install -y \"\$p\" || true; done")
        val ok = !output.startsWith("Error:")
        appendLog("Developer pack success=$ok")
        return ok
    }

    fun applyPreset(id: String): Boolean {
        createRecoveryPoint()
        val packages = when (id) {
            "coding" -> "git python nodejs clang cmake make"
            "school" -> "libreoffice firefox"
            "creative" -> "gimp inkscape imagemagick"
            "lightweight" -> "xfce4 xfce4-terminal thunar mousepad"
            "general" -> "firefox vlc libreoffice"
            "security" -> "openssh curl wget git python"
            else -> return false
        }
        val ok = !runtime.executeCommand("pkg install -y $packages").startsWith("Error:")
        appendLog("Preset $id success=$ok")
        return ok
    }

    fun installDistro(id: String): Boolean {
        val safe = when (id) { "debian", "ubuntu", "alpine" -> id; else -> return false }
        createRecoveryPoint()
        runtime.executeCommand("pkg install -y proot-distro")
        val output = runtime.executeCommand("proot-distro install $safe 2>&1 || true")
        val ok = File(prefix, "var/lib/proot-distro/containers/$safe").exists() ||
            File(prefix, "var/lib/proot-distro/installed-rootfs/$safe").exists()
        appendLog("Distro $safe success=$ok output=${output.takeLast(160)}")
        return ok
    }

    fun distroStatus(): Map<String, Boolean> {
        val modern = File(prefix, "var/lib/proot-distro/containers")
        val legacy = File(prefix, "var/lib/proot-distro/installed-rootfs")
        return listOf("debian", "ubuntu", "alpine").associateWith { id ->
            File(modern, id).exists() || File(legacy, id).exists()
        }
    }

    fun createRecoveryPoint(): Map<String, Any> = runCatching {
        desktopIntegration.createSnapshot(false)
    }.getOrElse {
        appendLog("Snapshot failed: ${it.message}")
        mapOf("error" to (it.message ?: "snapshot failed"))
    }

    fun exportLatestSnapshot(): Map<String, Any> {
        val latest = desktopIntegration.listSnapshots().firstOrNull()
            ?: return mapOf("ok" to false, "message" to "No snapshots available")
        val name = latest["name"]?.toString() ?: return mapOf("ok" to false, "message" to "Invalid snapshot")
        val source = File(context.filesDir, "snapshots/$name")
        val outDir = File(Environment.getExternalStorageDirectory(), "Download/DroidDeskBackups").apply { mkdirs() }
        val target = File(outDir, name)
        return runCatching {
            source.copyTo(target, overwrite = true)
            mapOf("ok" to true, "path" to target.absolutePath)
        }.getOrElse { mapOf("ok" to false, "message" to (it.message ?: "Export failed")) }
    }

    fun processSummary(): String =
        runtime.executeCommand("ps -A -o PID,PPID,STAT,%CPU,%MEM,NAME 2>/dev/null | head -n 30")

    fun logs(): String =
        if (logFile.isFile) logFile.readLines().takeLast(160).joinToString("\n") else "No Guardian logs yet."

    fun ensureNotificationBridgeScripts() {
        val localBin = File(home, ".local/bin").apply { mkdirs() }
        val notifier = File(localBin, "droiddesk-notify-android.py")
        notifier.writeText(
            "#!${File(prefix, "bin/python3").absolutePath}\n" +
            "import socket, sys\n" +
            "title = sys.argv[1] if len(sys.argv) > 1 else 'Linux'\n" +
            "body = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ''\n" +
            "payload = 'notify:' + title.replace('\\t',' ').replace('\\n',' ') + '\\t' + body.replace('\\t',' ').replace('\\n',' ')\n" +
            "s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n" +
            "s.connect('\\0droiddesk.android-app-launcher')\n" +
            "s.sendall((payload + '\\n').encode())\n"
        )
        notifier.setExecutable(true, false)
        val feed = File(context.filesDir, "bridge/android-notifications.tsv")
        feed.parentFile?.mkdirs()
        if (!feed.exists()) feed.createNewFile()
        val watcher = File(localBin, "droiddesk-notification-watch")
        watcher.writeText(
            "#!${File(prefix, "bin/bash").absolutePath}\n" +
            "feed='${feed.absolutePath}'\n" +
            "command -v notify-send >/dev/null 2>&1 || exit 0\n" +
            "tail -n 0 -F \"\$feed\" 2>/dev/null | while IFS=\$'\\t' read -r title body; do [ -n \"\$title\" ] && notify-send \"\$title\" \"\$body\"; done\n"
        )
        watcher.setExecutable(true, false)
    }

    private fun ensureOfflineRepairKit() {
        val localBin = File(home, ".local/bin").apply { mkdirs() }
        val repair = File(localBin, "droiddesk-repair")
        repair.writeText(
            "#!${File(prefix, "bin/bash").absolutePath}\n" +
            "echo 'DroidDesk offline repair kit'\n" +
            "for p in dbus-daemon xclip pulseaudio xfce4-panel; do command -v \"\$p\" >/dev/null || echo \"Missing: \$p\"; done\n" +
            "echo 'Use Guardian in the Android app for online package repair.'\n"
        )
        repair.setExecutable(true, false)
    }

    private fun processRunning(name: String): Boolean =
        runtime.executeCommand("pgrep -x '$name' >/dev/null 2>&1 && echo yes || echo no")
            .lineSequence().any { it.trim() == "yes" }

    private fun localIpv4(): String = runCatching {
        NetworkInterface.getNetworkInterfaces().toList()
            .flatMap { it.inetAddresses.toList() }
            .firstOrNull { !it.isLoopbackAddress && it.hostAddress?.contains(':') == false }
            ?.hostAddress ?: "127.0.0.1"
    }.getOrDefault("127.0.0.1")

    private fun appendLog(message: String) {
        logFile.parentFile?.mkdirs()
        val stamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date())
        logFile.appendText("[$stamp] $message\n")
        if (logFile.length() > 512 * 1024) {
            logFile.writeText(logFile.readLines().takeLast(1000).joinToString("\n", postfix = "\n"))
        }
    }

    private fun directorySize(root: File): Long {
        if (!root.exists()) return 0L
        var total = 0L
        root.walkTopDown().forEach { if (it.isFile) total += it.length() }
        return total
    }
}
