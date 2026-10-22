from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()

manifest = root / "app/android/app/src/main/AndroidManifest.xml"
text = manifest.read_text(encoding="utf-8")
if "android.permission.REQUEST_INSTALL_PACKAGES" not in text:
    text = text.replace(
        '    <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE" />',
        '    <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE" />\n'
        '    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />',
    )

provider = r'''
        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="${applicationId}.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>
'''
if "android.support.FILE_PROVIDER_PATHS" not in text:
    text = text.replace(
        '        <meta-data\n            android:name="flutterEmbedding"',
        provider + '\n        <meta-data\n            android:name="flutterEmbedding"',
    )
manifest.write_text(text, encoding="utf-8")

xml = root / "app/android/app/src/main/res/xml/file_paths.xml"
xml.parent.mkdir(parents=True, exist_ok=True)
xml.write_text(
    '''<?xml version="1.0" encoding="utf-8"?>
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <external-path name="external" path="." />
    <files-path name="files" path="." />
    <cache-path name="cache" path="." />
</paths>
''',
    encoding="utf-8",
)

bridge = root / "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/AndroidAppBridge.kt"
text = bridge.read_text(encoding="utf-8")
if "import android.os.Environment" not in text:
    text = text.replace(
        "import android.net.Uri\n",
        "import android.net.Uri\nimport android.os.Build\nimport android.os.Environment\nimport androidx.core.content.FileProvider\n",
        1,
    )

old = '''                } else if (command.startsWith("url:")) {
                    openUrl(context, command.removePrefix("url:"))
                } else {
                    launchPackage(context, command)
                }
'''
new = '''                } else if (command.startsWith("url:")) {
                    openUrl(context, command.removePrefix("url:"))
                } else if (command == "storage:request") {
                    requestAllFilesAccess(context)
                } else if (command.startsWith("install-apk:")) {
                    installApk(context, command.removePrefix("install-apk:"))
                } else {
                    launchPackage(context, command)
                }
'''
if old not in text:
    raise SystemExit("Android bridge command block changed")
text = text.replace(old, new, 1)

marker = "    private fun openUrl(context: Context, value: String): Boolean {\n"
idx = text.find(marker)
if idx < 0:
    raise SystemExit("openUrl marker missing")

helpers = r'''
    private fun requestAllFilesAccess(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return true
        if (Environment.isExternalStorageManager()) return true
        val appIntent = Intent(
            Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
            Uri.parse("package:${context.packageName}"),
        ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return runCatching {
            context.startActivity(appIntent)
            true
        }.recoverCatching {
            context.startActivity(
                Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            )
            true
        }.getOrDefault(false)
    }

    private fun installApk(context: Context, rawPath: String): Boolean {
        val file = File(rawPath)
        if (!file.isFile || file.extension.lowercase() != "apk") return false

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
            !context.packageManager.canRequestPackageInstalls()) {
            runCatching {
                context.startActivity(
                    Intent(
                        Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                        Uri.parse("package:${context.packageName}"),
                    ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                )
            }
            return false
        }

        return runCatching {
            val uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                file,
            )
            context.startActivity(
                Intent(Intent.ACTION_VIEW).apply {
                    setDataAndType(uri, "application/vnd.android.package-archive")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                },
            )
            true
        }.onFailure {
            Log.w(TAG, "Could not open APK installer for ${file.absolutePath}", it)
        }.getOrDefault(false)
    }

'''
text = text[:idx] + helpers + text[idx:]
bridge.write_text(text, encoding="utf-8")

print("Applied v2.0.5 Android storage and APK bridge.")
