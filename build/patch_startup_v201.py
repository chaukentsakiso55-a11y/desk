from pathlib import Path
import sys
import re

root = Path(sys.argv[1]).resolve()

def replace_once(path, old, new):
    p = root / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Expected block not found in {path}")
    if text.count(old) != 1:
        raise SystemExit(f"Expected exactly one match in {path}, found {text.count(old)}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")

def regex_once(path, pattern, repl):
    p = root / path
    text = p.read_text(encoding="utf-8")
    new, count = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE | re.DOTALL)
    if count != 1:
        raise SystemExit(f"Expected one regex match in {path}, found {count}")
    p.write_text(new, encoding="utf-8")

replace_once("app/pubspec.yaml", "version: 2.0.0+200\n", "version: 2.0.1+201\n")

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/NextManager.kt",
    """            "export DROIDDESK_PERFORMANCE_MODE=$mode\\n" +
            "export OMP_NUM_THREADS=$threads\\n" +
            "export PULSE_LATENCY_MSEC=$latency\\n" +
            "ulimit -v ${memoryLimitMB * 1024} 2>/dev/null || true\\n"
""",
    """            "export DROIDDESK_PERFORMANCE_MODE=$mode\\n" +
            "export OMP_NUM_THREADS=$threads\\n" +
            "export PULSE_LATENCY_MSEC=$latency\\n" +
            "export DROIDDESK_MEMORY_TARGET_MB=$memoryLimitMB\\n" +
            "export MALLOC_ARENA_MAX=2\\n"
""",
)

replace_once(
    "app/lib/state/app_state.dart",
    """      _installedDE = status['installedDE']?.toString() ?? '';

      if (_installedDE.isNotEmpty) {
""",
    """      _installedDE = status['installedDE']?.toString() ?? '';
      if (_installedDE.isNotEmpty) {
        _selectedDE = _installedDE;
      }

      if (_installedDE.isNotEmpty) {
""",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/MainActivity.kt",
    """                            val installed = linuxRuntime.getInstalledDE()
                            val ready = installed == desktopEnv ||
                                linuxRuntime.installDesktopEnvironmentNative(desktopEnv)
                            if (!ready) {
                                Log.e(TAG, "Native Termux desktop setup failed; session was not launched")
""",
    """                            val installed = linuxRuntime.getInstalledDE()
                            val chosenDesktop = when {
                                linuxRuntime.isDesktopAvailable(desktopEnv) -> desktopEnv
                                installed.isNotEmpty() && linuxRuntime.isDesktopAvailable(installed) -> installed
                                else -> ""
                            }
                            val ready = chosenDesktop.isNotEmpty()
                            if (!ready) {
                                Log.e(TAG, "No installed desktop is ready; session was not launched")
""",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/MainActivity.kt",
    '"Native Linux setup failed. Check the setup log.",',
    '"No installed Linux desktop is ready. Open DroidDesk Next → Guardian.",',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/MainActivity.kt",
    '''                                val intent = Intent(this@MainActivity, com.orailnoor.droiddesk.view.DesktopActivity::class.java).apply {
                                    putExtra("startSession", !linuxRuntime.isRunning())
                                    putExtra("mode", "termux")
                                    putExtra("de", desktopEnv)
                                }
''',
    '''                                val intent = Intent(this@MainActivity, com.orailnoor.droiddesk.view.DesktopActivity::class.java).apply {
                                    putExtra("startSession", !linuxRuntime.isRunning())
                                    putExtra("mode", "termux")
                                    putExtra("de", chosenDesktop)
                                }
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    "        @Volatile private var dbusProcess: Process? = null\n",
    "        @Volatile private var dbusProcess: Process? = null\n        @Volatile private var watchdogDesktop: String? = null\n",
)

status_helpers = r'''
    fun isDesktopAvailable(desktopEnv: String): Boolean {
        return when (normalizedDesktop(desktopEnv)) {
            "mate" -> File(binDir, "mate-session").canExecute() || File(binDir, "mate-panel").canExecute()
            "lxqt" -> File(binDir, "lxqt-session").canExecute() || File(binDir, "lxqt-panel").canExecute()
            "kde" -> File(binDir, "startplasma-x11").canExecute() || File(binDir, "plasmashell").canExecute()
            else -> File(binDir, "xfce4-session").canExecute() || File(binDir, "xfce4-panel").canExecute()
        }
    }

    private fun desktopStartupLogFile(): File =
        File(baseDir, "next/desktop-startup.log").apply { parentFile?.mkdirs() }

    fun getLastDesktopFailure(): String {
        val file = desktopStartupLogFile()
        if (!file.isFile) return "The Linux desktop process did not become ready."
        val useful = file.readLines()
            .map(String::trim)
            .filter(String::isNotEmpty)
            .filterNot { it.startsWith("DIAG: PulseAudio") }
            .takeLast(12)
        val preferred = useful.lastOrNull {
            val value = it.lowercase()
            value.contains("error") ||
                value.contains("failed") ||
                value.contains("cannot") ||
                value.contains("not found") ||
                value.contains("fatal") ||
                value.contains("killed")
        } ?: useful.lastOrNull()
        return preferred?.take(180) ?: "The Linux desktop process exited before it was ready."
    }

'''
replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    "    fun getGraphicsMode(): String {\n",
    status_helpers + "    fun getGraphicsMode(): String {\n",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''            "mate" -> "mate-settings-daemon >/dev/null 2>&1 & marco --replace >/dev/null 2>&1 & caja --no-default-window >/dev/null 2>&1 & exec mate-panel"
''',
    '''            "mate" -> "mate-session"
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        Log.i(TAG, "Starting native Termux session for $selectedDesktop")

        val bashBin = File(prefixDir, "bin/bash").absolutePath
''',
    '''        Log.i(TAG, "Starting native Termux session for $selectedDesktop")
        desktopStartupLogFile().writeText(
            "DroidDesk desktop startup\\nDesktop=$selectedDesktop\\nGraphics=${getGraphicsMode()}\\n"
        )

        val bashBin = File(prefixDir, "bin/bash").absolutePath
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        sessionProcess = startedSession
        startDesktopWatchdog(selectedDesktop)

        Thread {
''',
    '''        sessionProcess = startedSession

        Thread {
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''                    Log.d(TAG, "DESKTOP: " + String(buffer, 0, charsRead))
''',
    '''                    val chunk = String(buffer, 0, charsRead)
                    Log.d(TAG, "DESKTOP: $chunk")
                    runCatching { desktopStartupLogFile().appendText(chunk) }
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''            } catch (error: java.io.IOException) {
                // destroyForcibly() closes the pipe during a normal shutdown.
                Log.d(TAG, "Desktop output stream closed")
            }
        }.start()

        Log.i(TAG, "Termux session started")
''',
    '''            } catch (error: java.io.IOException) {
                Log.d(TAG, "Desktop output stream closed")
            } finally {
                runCatching {
                    if (!startedSession.isAlive) {
                        desktopStartupLogFile().appendText(
                            "\\n[desktop process exited code=${startedSession.exitValue()}]\\n"
                        )
                    }
                }
            }
        }.start()

        Log.i(TAG, "Termux session started")
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''    private fun startDesktopWatchdog(desktopEnv: String) {
        val de = normalizedDesktop(desktopEnv)
        Thread({
            while (sessionProcess?.isAlive == true) {
''',
    '''    private fun startDesktopWatchdog(desktopEnv: String) {
        val de = normalizedDesktop(desktopEnv)
        if (watchdogDesktop == de) return
        watchdogDesktop = de
        Thread({
            while (sessionProcess?.isAlive == true && watchdogDesktop == de) {
''',
)

regex_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    r'''    fun waitForDesktopReady\(desktopEnv: String = "xfce4", timeoutMs: Long = 45_000\): Boolean \{.*?^    \}\n\n    fun stopSession\(\) \{''',
    r'''    fun waitForDesktopReady(desktopEnv: String = "xfce4", timeoutMs: Long = 25_000): Boolean {
        val selected = normalizedDesktop(desktopEnv)
        val processes = when (selected) {
            "lxqt" -> listOf("lxqt-session", "lxqt-panel", "pcmanfm-qt")
            "mate" -> listOf("mate-session", "mate-panel", "marco", "caja")
            "kde" -> listOf("plasmashell")
            else -> listOf("xfce4-panel", "xfdesktop", "xfwm4")
        }
        val deadline = System.currentTimeMillis() + timeoutMs
        val grace = System.currentTimeMillis() + 2_000
        while (System.currentTimeMillis() < deadline) {
            if (System.currentTimeMillis() > grace && sessionProcess?.isAlive != true) {
                Log.e(TAG, "Desktop process exited before readiness: ${getLastDesktopFailure()}")
                return false
            }
            val check = processes.joinToString(" || ") { "pgrep -x '$it' >/dev/null" }
            val ready = runCatching {
                ProcessBuilder(File(binDir, "bash").absolutePath, "-c", check)
                    .directory(homeDir)
                    .redirectErrorStream(true)
                    .also { builder ->
                        builder.environment().clear()
                        builder.environment().putAll(getTermuxEnv())
                    }
                    .start()
                    .waitFor() == 0
            }.getOrDefault(false)
            if (ready) {
                Thread.sleep(500)
                startDesktopWatchdog(selected)
                return true
            }
            Thread.sleep(200)
        }
        Log.w(TAG, "Timed out waiting for $desktopEnv. ${getLastDesktopFailure()}")
        return false
    }

    fun stopSession() {''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        sessionProcess = null
        dbusProcess?.destroyForcibly()
        dbusProcess = null
''',
    '''        sessionProcess = null
        watchdogDesktop = null
        dbusProcess?.destroyForcibly()
        dbusProcess = null
''',
)

regex_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/view/DesktopActivity.kt",
    r'''            if \(!ready && sessionMode == "termux" && desktopEnv != "xfce4" && !recoveryAttempted\) \{.*?                return@runOnUiThread\n            \}\n''',
    r'''            if (!ready && sessionMode == "termux" && desktopEnv != "xfce4" && !recoveryAttempted) {
                recoveryAttempted = true
                if (linuxRuntime.isDesktopAvailable("xfce4")) {
                    loadingStatus?.text = "Recovery Mode: switching to XFCE"
                    loadingEstimate?.text = "Starting the already-installed safe desktop"
                    Thread({
                        linuxRuntime.stopSession()
                        desktopEnv = "xfce4"
                        linuxRuntime.startSession("xfce4", "x11")
                        revealDesktop(linuxRuntime.waitForDesktopReady("xfce4", 25_000))
                    }, "DroidDeskRecovery").start()
                    return@runOnUiThread
                }
            }
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/view/DesktopActivity.kt",
    '''                loadingStatus?.text = "Linux desktop failed to start"
                loadingEstimate?.text = "Returning to DroidDesk so you can retry"
''',
    '''                loadingStatus?.text = "Linux desktop failed to start"
                loadingEstimate?.text = if (sessionMode == "termux") {
                    linuxRuntime.getLastDesktopFailure()
                } else {
                    "Returning to DroidDesk. Run Guardian before retrying."
                }
''',
)

print("Applied DroidDesk Next v2.0.1 startup fixes.")
