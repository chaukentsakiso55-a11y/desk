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

def insert_before_last_brace(path, content):
    p = root / path
    text = p.read_text(encoding="utf-8")
    idx = text.rfind("}")
    if idx < 0:
        raise SystemExit(f"No closing brace in {path}")
    p.write_text(text[:idx] + content + "\n" + text[idx:], encoding="utf-8")

replace_once(
    "app/pubspec.yaml",
    "version: 1.0.5+105\n",
    "version: 2.0.0+200\n",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/MainActivity.kt",
    "import com.orailnoor.droiddesk.runtime.DesktopIntegration\n",
    "import com.orailnoor.droiddesk.runtime.DesktopIntegration\nimport com.orailnoor.droiddesk.runtime.NextManager\n",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/MainActivity.kt",
    "    private lateinit var desktopIntegration: DesktopIntegration\n",
    "    private lateinit var desktopIntegration: DesktopIntegration\n    private lateinit var nextManager: NextManager\n",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/MainActivity.kt",
    "        desktopIntegration = DesktopIntegration(this)\n",
    "        desktopIntegration = DesktopIntegration(this)\n        nextManager = NextManager(this, linuxRuntime, desktopIntegration)\n",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/MainActivity.kt",
    """                    if (height > 720) {
                        val scale = 720.0 / height
                        width = (width * scale).toInt()
                        height = 720
                    }
""",
    """                    width = width.coerceIn(800, 3840)
                    height = height.coerceIn(480, 2160)
""",
)

handlers = r'''
                // ── DroidDesk Next ──
                "getNextStatus" -> result.success(nextManager.status())
                "getGuardianReport" -> result.success(nextManager.guardianReport())

                "runGuardianRepair" -> {
                    thread(name = "guardian-repair") {
                        val report = runCatching { nextManager.repair() }
                            .getOrElse { mapOf("repairCompleted" to false, "error" to (it.message ?: "repair failed")) }
                        runOnUiThread { result.success(report) }
                    }
                }

                "setNextPerformance" -> {
                    val mode = call.argument<String>("mode") ?: "balanced"
                    val memory = call.argument<Int>("memoryLimitMB") ?: 2048
                    result.success(nextManager.setPerformanceMode(mode, memory))
                }

                "configureNextSharedFolders" -> result.success(nextManager.configureSharedFolders())
                "cleanNextCaches" -> result.success(nextManager.cleanCaches())

                "toggleNextSsh" -> {
                    val enable = call.argument<Boolean>("enable") ?: false
                    thread(name = "next-ssh") {
                        val value = nextManager.toggleSsh(enable)
                        runOnUiThread { result.success(value) }
                    }
                }

                "toggleNextVnc" -> {
                    val enable = call.argument<Boolean>("enable") ?: false
                    thread(name = "next-vnc") {
                        val value = nextManager.toggleVnc(enable)
                        runOnUiThread { result.success(value) }
                    }
                }

                "installNextDevPack" -> {
                    thread(name = "next-dev-pack") {
                        val ok = nextManager.installDevPack()
                        runOnUiThread { result.success(ok) }
                    }
                }

                "applyNextPreset" -> {
                    val preset = call.argument<String>("preset") ?: "general"
                    thread(name = "next-preset") {
                        val ok = nextManager.applyPreset(preset)
                        runOnUiThread { result.success(ok) }
                    }
                }

                "installNextDistro" -> {
                    val distro = call.argument<String>("distro") ?: "debian"
                    thread(name = "next-distro") {
                        val ok = nextManager.installDistro(distro)
                        runOnUiThread { result.success(ok) }
                    }
                }

                "installNextDesktop" -> {
                    val de = call.argument<String>("de") ?: "xfce4"
                    thread(name = "next-desktop-install") {
                        val ok = linuxRuntime.installDesktopEnvironmentNative(de)
                        runOnUiThread { result.success(ok) }
                    }
                }

                "createRecoveryPoint" -> {
                    thread(name = "next-snapshot") {
                        val value = nextManager.createRecoveryPoint()
                        runOnUiThread { result.success(value) }
                    }
                }

                "exportNextSnapshot" -> {
                    thread(name = "next-export") {
                        val value = nextManager.exportLatestSnapshot()
                        runOnUiThread { result.success(value) }
                    }
                }

                "getNextProcesses" -> {
                    thread(name = "next-processes") {
                        val value = nextManager.processSummary()
                        runOnUiThread { result.success(value) }
                    }
                }

                "getNextLogs" -> result.success(nextManager.logs())

                "startSafeDesktop" -> {
                    thread(name = "next-safe-desktop") {
                        if (chrootRuntime.hasRoot()) {
                            chrootRuntime.stopSession()
                            runOnUiThread {
                                startActivity(Intent(this@MainActivity, com.orailnoor.droiddesk.view.DesktopActivity::class.java).apply {
                                    putExtra("startSession", true)
                                    putExtra("mode", "chroot")
                                    putExtra("de", "xfce4")
                                })
                                result.success(true)
                            }
                        } else {
                            linuxRuntime.stopSession()
                            val ok = linuxRuntime.installDesktopEnvironmentNative("xfce4")
                            if (!ok) {
                                runOnUiThread { result.success(false) }
                            } else {
                                runOnUiThread {
                                    startActivity(Intent(this@MainActivity, com.orailnoor.droiddesk.view.DesktopActivity::class.java).apply {
                                        putExtra("startSession", true)
                                        putExtra("mode", "termux")
                                        putExtra("de", "xfce4")
                                    })
                                    result.success(true)
                                }
                            }
                        }
                    }
                }

'''
replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/MainActivity.kt",
    "                // ── Start Linux session ──\n",
    handlers + "                // ── Start Linux session ──\n",
)

bridge_methods = r'''
  // ── DroidDesk Next ──
  static Future<Map<String, dynamic>> getNextStatus() async {
    final value = await _channel.invokeMethod<Map<dynamic, dynamic>>('getNextStatus');
    return Map<String, dynamic>.from(value ?? const {});
  }

  static Future<Map<String, dynamic>> getGuardianReport() async {
    final value = await _channel.invokeMethod<Map<dynamic, dynamic>>('getGuardianReport');
    return Map<String, dynamic>.from(value ?? const {});
  }

  static Future<Map<String, dynamic>> runGuardianRepair() async {
    final value = await _channel.invokeMethod<Map<dynamic, dynamic>>('runGuardianRepair');
    return Map<String, dynamic>.from(value ?? const {});
  }

  static Future<bool> setNextPerformance(String mode, int memoryLimitMB) async =>
      await _channel.invokeMethod<bool>('setNextPerformance', {
        'mode': mode,
        'memoryLimitMB': memoryLimitMB,
      }) ?? false;

  static Future<Map<String, dynamic>> configureNextSharedFolders() async {
    final value = await _channel.invokeMethod<Map<dynamic, dynamic>>('configureNextSharedFolders');
    return Map<String, dynamic>.from(value ?? const {});
  }

  static Future<Map<String, dynamic>> cleanNextCaches() async {
    final value = await _channel.invokeMethod<Map<dynamic, dynamic>>('cleanNextCaches');
    return Map<String, dynamic>.from(value ?? const {});
  }

  static Future<Map<String, dynamic>> toggleNextSsh(bool enable) async {
    final value = await _channel.invokeMethod<Map<dynamic, dynamic>>('toggleNextSsh', {'enable': enable});
    return Map<String, dynamic>.from(value ?? const {});
  }

  static Future<Map<String, dynamic>> toggleNextVnc(bool enable) async {
    final value = await _channel.invokeMethod<Map<dynamic, dynamic>>('toggleNextVnc', {'enable': enable});
    return Map<String, dynamic>.from(value ?? const {});
  }

  static Future<bool> installNextDevPack() async =>
      await _channel.invokeMethod<bool>('installNextDevPack') ?? false;

  static Future<bool> applyNextPreset(String preset) async =>
      await _channel.invokeMethod<bool>('applyNextPreset', {'preset': preset}) ?? false;

  static Future<bool> installNextDistro(String distro) async =>
      await _channel.invokeMethod<bool>('installNextDistro', {'distro': distro}) ?? false;

  static Future<bool> installNextDesktop(String de) async =>
      await _channel.invokeMethod<bool>('installNextDesktop', {'de': de}) ?? false;

  static Future<Map<String, dynamic>> createRecoveryPoint() async {
    final value = await _channel.invokeMethod<Map<dynamic, dynamic>>('createRecoveryPoint');
    return Map<String, dynamic>.from(value ?? const {});
  }

  static Future<Map<String, dynamic>> exportNextSnapshot() async {
    final value = await _channel.invokeMethod<Map<dynamic, dynamic>>('exportNextSnapshot');
    return Map<String, dynamic>.from(value ?? const {});
  }

  static Future<String> getNextProcesses() async =>
      await _channel.invokeMethod<String>('getNextProcesses') ?? '';

  static Future<String> getNextLogs() async =>
      await _channel.invokeMethod<String>('getNextLogs') ?? '';

  static Future<bool> startSafeDesktop() async =>
      await _channel.invokeMethod<bool>('startSafeDesktop') ?? false;
'''
insert_before_last_brace("app/lib/services/platform_bridge.dart", bridge_methods)

replace_once(
    "app/lib/screens/home_screen.dart",
    "import 'package:droiddesk/screens/desktop_tools_screen.dart';\n",
    "import 'package:droiddesk/screens/desktop_tools_screen.dart';\nimport 'package:droiddesk/screens/next_center_screen.dart';\n",
)

next_card = r'''                      _ActionCard(
                        icon: Icons.shield_rounded,
                        title: 'DroidDesk Next',
                        subtitle:
                            'Guardian, recovery, performance, backups, bridges, displays, SSH, VNC, distros, and developer tools',
                        color: DroidTheme.accent,
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => const NextCenterScreen(),
                            ),
                          );
                        },
                      ),

                      const SizedBox(height: 10),

'''
replace_once(
    "app/lib/screens/home_screen.dart",
    """                      _ActionCard(
                        icon: Icons.apps_rounded,
                        title: 'Add applications',
""",
    next_card + """                      _ActionCard(
                        icon: Icons.apps_rounded,
                        title: 'Add applications',
""",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''            export DBUS_SESSION_BUS_ADDRESS="unix:path=${dbusSocket.absolutePath}"
''',
    '''            export DBUS_SESSION_BUS_ADDRESS="unix:path=${dbusSocket.absolutePath}"

            [ -f "${homeDir.absolutePath}/.config/droiddesk/session-profile.sh" ] &&
                . "${homeDir.absolutePath}/.config/droiddesk/session-profile.sh"
            [ -x "${homeDir.absolutePath}/.local/bin/droiddesk-notification-watch" ] &&
                "${homeDir.absolutePath}/.local/bin/droiddesk-notification-watch" >/dev/null 2>&1 &
''',
)

watchdog = r'''
    private fun startDesktopWatchdog(desktopEnv: String) {
        val de = normalizedDesktop(desktopEnv)
        Thread({
            while (sessionProcess?.isAlive == true) {
                try {
                    Thread.sleep(5_000)
                    val command = when (de) {
                        "mate" ->
                            "pgrep -x marco >/dev/null || marco --replace >/dev/null 2>&1 & " +
                            "pgrep -x mate-panel >/dev/null || mate-panel >/dev/null 2>&1 &"
                        "lxqt" ->
                            "pgrep -x lxqt-panel >/dev/null || lxqt-panel >/dev/null 2>&1 &"
                        "kde" ->
                            "pgrep -x plasmashell >/dev/null || plasmashell --replace >/dev/null 2>&1 &"
                        else ->
                            "pgrep -x xfdesktop >/dev/null || xfdesktop >/dev/null 2>&1 & " +
                            "pgrep -x xfce4-panel >/dev/null || xfce4-panel >/dev/null 2>&1 &"
                    }
                    ProcessBuilder(File(binDir, "bash").absolutePath, "-c", command)
                        .directory(homeDir)
                        .redirectErrorStream(true)
                        .also { builder ->
                            builder.environment().clear()
                            builder.environment().putAll(getTermuxEnv())
                            builder.environment()["DISPLAY"] = ":0"
                            builder.environment()["DBUS_SESSION_BUS_ADDRESS"] =
                                "unix:path=${File(tmpDir, "dbus-session").absolutePath}"
                        }
                        .start()
                        .waitFor()
                } catch (_: InterruptedException) {
                    Thread.currentThread().interrupt()
                    return@Thread
                } catch (error: Throwable) {
                    Log.w(TAG, "Desktop watchdog check failed", error)
                }
            }
        }, "DroidDeskDesktopWatchdog").apply { isDaemon = true }.start()
    }

'''
replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    "    /** Wait until the desktop shell processes that paint the first frame exist. */\n",
    watchdog + "    /** Wait until the desktop shell processes that paint the first frame exist. */\n",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        sessionProcess = startedSession

        Thread {
''',
    '''        sessionProcess = startedSession
        startDesktopWatchdog(selectedDesktop)

        Thread {
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/view/DesktopActivity.kt",
    "    private var desktopRevealed = false\n",
    "    private var desktopRevealed = false\n    private var recoveryAttempted = false\n",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/view/DesktopActivity.kt",
    '''            if (!ready) {
                loadingMessageHandler.removeCallbacks(loadingMessageTicker)
                loadingMessageHandler.removeCallbacks(loadingEstimateTicker)
                loadingStatus?.text = "Linux desktop failed to start"
''',
    '''            if (!ready && sessionMode == "termux" && desktopEnv != "xfce4" && !recoveryAttempted) {
                recoveryAttempted = true
                loadingStatus?.text = "Recovery Mode: switching to XFCE"
                loadingEstimate?.text = "Repairing the desktop session..."
                Thread({
                    linuxRuntime.stopSession()
                    val installed = linuxRuntime.installDesktopEnvironmentNative("xfce4")
                    if (installed) {
                        desktopEnv = "xfce4"
                        linuxRuntime.startSession("xfce4", "x11")
                        revealDesktop(linuxRuntime.waitForDesktopReady("xfce4", 45_000))
                    } else {
                        revealDesktop(false)
                    }
                }, "DroidDeskRecovery").start()
                return@runOnUiThread
            }
            if (!ready) {
                loadingMessageHandler.removeCallbacks(loadingMessageTicker)
                loadingMessageHandler.removeCallbacks(loadingEstimateTicker)
                loadingStatus?.text = "Linux desktop failed to start"
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/AndroidAppBridge.kt",
    '''                if (command.startsWith("action:")) {
                    launchSystemAction(context, command.removePrefix("action:"))
                } else {
                    launchPackage(context, command)
                }
''',
    '''                if (command.startsWith("action:")) {
                    launchSystemAction(context, command.removePrefix("action:"))
                } else if (command.startsWith("notify:")) {
                    showLinuxNotification(context, command.removePrefix("notify:"))
                } else {
                    launchPackage(context, command)
                }
''',
)

notification_method = r'''
    private fun showLinuxNotification(context: Context, payload: String) {
        val parts = payload.split('\t', limit = 2)
        val title = parts.getOrNull(0)?.take(80).orEmpty().ifBlank { "Linux" }
        val body = parts.getOrNull(1)?.take(240).orEmpty()
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as android.app.NotificationManager
        val channelId = "droiddesk_linux"
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                android.app.NotificationChannel(
                    channelId,
                    "Linux desktop",
                    android.app.NotificationManager.IMPORTANCE_DEFAULT,
                ),
            )
        }
        val builder = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            android.app.Notification.Builder(context, channelId)
        } else {
            @Suppress("DEPRECATION")
            android.app.Notification.Builder(context)
        }
        manager.notify(
            (System.currentTimeMillis() and 0x7fffffff).toInt(),
            builder
                .setSmallIcon(android.R.drawable.stat_notify_more)
                .setContentTitle(title)
                .setContentText(body)
                .setAutoCancel(true)
                .build(),
        )
    }

'''
replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/AndroidAppBridge.kt",
    "    private fun launchPackage(context: Context, packageName: String): Boolean {\n",
    notification_method + "    private fun launchPackage(context: Context, packageName: String): Boolean {\n",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/AndroidAppBridge.kt",
    '''            "battery" -> Settings.ACTION_BATTERY_SAVER_SETTINGS
            else -> Settings.ACTION_SETTINGS
''',
    '''            "battery" -> Settings.ACTION_BATTERY_SAVER_SETTINGS
            "storage" -> if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
                Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION
            } else {
                Settings.ACTION_APPLICATION_DETAILS_SETTINGS
            }
            "notification_access" -> Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS
            else -> Settings.ACTION_SETTINGS
''',
)

replace_once(
    "app/android/app/src/main/AndroidManifest.xml",
    '''        <!-- Foreground Service: keeps the chroot or native Termux session alive -->
''',
    '''        <service
            android:name=".runtime.DroidDeskNotificationListener"
            android:label="DroidDesk Notification Bridge"
            android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE"
            android:exported="true">
            <intent-filter>
                <action android:name="android.service.notification.NotificationListenerService" />
            </intent-filter>
        </service>

        <!-- Foreground Service: keeps the chroot or native Termux session alive -->
''',
)

print("Applied DroidDesk Next feature layer.")
