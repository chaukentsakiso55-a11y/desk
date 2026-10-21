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

def insert_before(path, marker, content):
    p = root / path
    text = p.read_text(encoding="utf-8")
    if marker not in text:
        raise SystemExit(f"Marker not found in {path}")
    p.write_text(text.replace(marker, content + marker, 1), encoding="utf-8")

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/AndroidAppBridge.kt",
    '''        syncUtilityLaunchers(homeDir, pythonPath, launcherPath, sessionPath(homeDir))
        syncDockLaunchers(context, homeDir, activities, appsDir)
''',
    '''        syncUtilityLaunchers(homeDir, pythonPath, launcherPath, sessionPath(homeDir))
        syncDockLaunchers(context, homeDir, activities, appsDir)
        syncSelectedDesktopLaunchers(context, homeDir, activities, appsDir)
''',
)

selected = r'''
    private fun syncSelectedDesktopLaunchers(
        context: Context,
        homeDir: File,
        activities: List<android.content.pm.ResolveInfo>,
        appsDir: File,
    ) {
        val desktopDir = File(homeDir, "Desktop").apply { mkdirs() }
        desktopDir.listFiles()
            ?.filter { it.name.startsWith("DroidDesk-Android-") && it.extension == "desktop" }
            ?.forEach { it.delete() }

        val installed = activities.associateBy { it.activityInfo.packageName }
        getDockPackages(context).forEach { packageName ->
            if (!installed.containsKey(packageName)) return@forEach
            val safeName = packageName.replace(Regex("[^A-Za-z0-9_.-]"), "_")
            val source = File(appsDir, "${'$'}safeName.desktop")
            if (!source.isFile) return@forEach
            val target = File(desktopDir, "DroidDesk-Android-${'$'}safeName.desktop")
            source.copyTo(target, overwrite = true)
            target.setExecutable(true, false)
        }
    }

'''
insert_before(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/AndroidAppBridge.kt",
    "    private fun syncDockLaunchers(\n",
    selected,
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/AndroidAppBridge.kt",
    "val safe = packages.filter { it in installed }.distinct().take(8)",
    "val safe = packages.filter { it in installed }.distinct().take(16)",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/AndroidAppBridge.kt",
    '''                } else if (command.startsWith("notify:")) {
                    showLinuxNotification(context, command.removePrefix("notify:"))
                } else {
                    launchPackage(context, command)
                }
''',
    '''                } else if (command.startsWith("notify:")) {
                    showLinuxNotification(context, command.removePrefix("notify:"))
                } else if (command.startsWith("url:")) {
                    openUrl(context, command.removePrefix("url:"))
                } else {
                    launchPackage(context, command)
                }
''',
)

url_fn = r'''
    private fun openUrl(context: Context, value: String): Boolean {
        val uri = runCatching { Uri.parse(value) }.getOrNull() ?: return false
        if (uri.scheme !in setOf("http", "https")) return false
        return runCatching {
            context.startActivity(
                Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            )
            true
        }.onFailure { Log.w(TAG, "Could not open URL", it) }.getOrDefault(false)
    }

'''
insert_before(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/AndroidAppBridge.kt",
    "    private fun launchPackage(context: Context, packageName: String): Boolean {\n",
    url_fn,
)

replace_once(
    "app/lib/screens/desktop_tools_screen.dart",
    "Tab(icon: Icon(Icons.dock_rounded), text: 'Dock'),",
    "Tab(icon: Icon(Icons.apps_rounded), text: 'Android apps'),",
)
replace_once(
    "app/lib/screens/desktop_tools_screen.dart",
    "Text('PINNED', style: DroidTheme.label),",
    "Text('VISIBLE ON LINUX DESKTOP', style: DroidTheme.label),",
)
replace_once(
    "app/lib/screens/desktop_tools_screen.dart",
    "Text('${_dockPackages.length}/8', style: DroidTheme.bodySm),",
    "Text('${_dockPackages.length}/16', style: DroidTheme.bodySm),",
)
replace_once(
    "app/lib/screens/desktop_tools_screen.dart",
    "_dockPackages.length >= 8",
    "_dockPackages.length >= 16",
)

print("Applied v2.0.3 Android app integration.")
