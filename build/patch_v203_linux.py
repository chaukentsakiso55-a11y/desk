from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()

def replace_once(path, old, new):
    p = root / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Expected block not found in {path}: {old[:120]!r}")
    if text.count(old) != 1:
        raise SystemExit(f"Expected exactly one match in {path}, found {text.count(old)}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")

def insert_before(path, marker, content):
    p = root / path
    text = p.read_text(encoding="utf-8")
    if marker not in text:
        raise SystemExit(f"Marker not found in {path}")
    p.write_text(text.replace(marker, content + marker, 1), encoding="utf-8")

replace_once("app/pubspec.yaml", "version: 2.0.2+202\n", "version: 2.0.3+203\n")
replace_once(
    "app/pubspec.yaml",
    "    - assets/socket_hook.c\n",
    "    - assets/socket_hook.c\n    - assets/ember/ember_server.py\n",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '"mate" -> "mate mate-terminal gvfs mate-applets"',
    '"mate" -> "mate mate-terminal gvfs mate-applets mate-notification-daemon thunar"',
)
replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    'installPackageGroup("pkg install -y glib gvfs mate-applets mate-terminal")',
    'installPackageGroup("pkg install -y glib gvfs mate-applets mate-terminal mate-notification-daemon thunar")',
)
replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '"la", "prl", "sh", "pl", "py", "rb", "json", "ini",',
    '"la", "prl", "sh", "pl", "py", "rb", "json", "ini",\n                            "mate-panel-applet", "panel-applet", "applet",',
)

helpers = r'''
    private fun installDroidDeskBuiltIns() {
        val desktopDir = File(homeDir, "Desktop").apply { mkdirs() }
        val localApps = File(homeDir, ".local/share/applications").apply { mkdirs() }
        val localBin = File(homeDir, ".local/bin").apply { mkdirs() }
        val emberDir = File(homeDir, ".local/share/droiddesk-ember").apply { mkdirs() }
        val emberServer = File(emberDir, "ember_server.py")

        runCatching {
            context.assets.open("flutter_assets/assets/ember/ember_server.py").use { input ->
                emberServer.outputStream().use { output -> input.copyTo(output) }
            }
        }.onFailure { Log.w(TAG, "Could not install Ember asset", it) }

        val emberLauncher = File(localBin, "ember")
        emberLauncher.writeText(
            """
            #!${File(binDir, "bash").absolutePath}
            export HOME="${homeDir.absolutePath}"
            export PREFIX="${prefixDir.absolutePath}"
            export DISPLAY="${'$'}{DISPLAY:-:0}"
            url="http://127.0.0.1:8765/"
            mkdir -p "${File(homeDir, ".cache").absolutePath}"
            if ! curl -fsS --max-time 1 "${'$'}url" >/dev/null 2>&1; then
              nohup "${File(binDir, "python3").absolutePath}" "${emberServer.absolutePath}" \
                >"${File(homeDir, ".cache/ember.log").absolutePath}" 2>&1 &
              for _ in 1 2 3 4 5 6 7 8 9 10; do
                curl -fsS --max-time 1 "${'$'}url" >/dev/null 2>&1 && break
                sleep 0.2
              done
            fi
            if command -v firefox >/dev/null 2>&1; then
              firefox --new-window "${'$'}url" >/dev/null 2>&1 &
            elif [ -x "${File(localBin, "droiddesk-launch-android-app.py").absolutePath}" ]; then
              "${File(binDir, "python3").absolutePath}" \
                "${File(localBin, "droiddesk-launch-android-app.py").absolutePath}" \
                "url:${'$'}url"
            fi
            """.trimIndent() + "\n",
        )
        emberLauncher.setExecutable(true, false)

        fun writeDesktop(file: File, name: String, comment: String, exec: String, icon: String, terminal: Boolean) {
            file.writeText(
                """
                [Desktop Entry]
                Version=1.0
                Type=Application
                Name=${'$'}name
                Comment=${'$'}comment
                Exec=${'$'}exec
                Icon=${'$'}icon
                Terminal=${if (terminal) "true" else "false"}
                Categories=Utility;Development;
                StartupNotify=true
                """.trimIndent() + "\n",
            )
            file.setExecutable(true, false)
        }

        val python = File(localApps, "droiddesk-python.desktop")
        writeDesktop(
            python,
            "Python",
            "Built-in Python 3 runtime",
            File(binDir, "python3").absolutePath,
            "utilities-terminal",
            true,
        )
        val ember = File(localApps, "droiddesk-ember.desktop")
        writeDesktop(
            ember,
            "Ember",
            "MARK LI-style assistant, browser control and WhatsApp interface",
            emberLauncher.absolutePath,
            "applications-development",
            false,
        )
        val home = File(localApps, "droiddesk-home.desktop")
        writeDesktop(
            home,
            "Linux Home",
            "Open your DroidDesk files",
            "${File(binDir, "thunar").absolutePath} ${homeDir.absolutePath}",
            "folder-home",
            false,
        )

        listOf(
            python to "DroidDesk-Python.desktop",
            ember to "DroidDesk-Ember.desktop",
            home to "DroidDesk-Home.desktop",
        ).forEach { (source, name) ->
            val target = File(desktopDir, name)
            source.copyTo(target, overwrite = true)
            target.setExecutable(true, false)
        }
    }

    private fun syncStoreDesktopLaunchers() {
        val desktopDir = File(homeDir, "Desktop").apply { mkdirs() }
        desktopDir.listFiles()
            ?.filter { it.name.startsWith("DroidDesk-App-") && it.extension == "desktop" }
            ?.forEach { it.delete() }

        val appDir = File(prefixDir, "share/applications")
        if (!appDir.isDirectory) return

        storeInstalledPackages().forEach { packageName ->
            val listFile = File(prefixDir, "var/lib/dpkg/info/${'$'}packageName.list")
            if (!listFile.isFile) return@forEach
            listFile.readLines()
                .filter { it.contains("/share/applications/") && it.endsWith(".desktop") }
                .map { File(it).name }
                .distinct()
                .forEach { desktopName ->
                    val source = File(appDir, desktopName)
                    if (!source.isFile) return@forEach
                    if (Regex("(?im)^NoDisplay=true\\s*${'$'}").containsMatchIn(source.readText())) return@forEach
                    val safePackage = packageName.replace(Regex("[^A-Za-z0-9_.-]"), "_")
                    val target = File(desktopDir, "DroidDesk-App-${'$'}safePackage-${'$'}desktopName")
                    source.copyTo(target, overwrite = true)
                    target.setExecutable(true, false)
                }
        }
    }

    private fun prepareMateV203() {
        val marker = File(prefixDir, ".mate_compat_v203")
        if (marker.exists()) return
        val required = listOf(
            "gvfs",
            "mate-applets",
            "mate-notification-daemon",
            "mate-terminal",
            "thunar",
        )
        val missing = required.filterNot(::isDpkgPackageInstalled)
        if (missing.isNotEmpty()) {
            installPackageGroup("pkg install -y ${'$'}{missing.joinToString(" ")}")
        }
        patchShebangs(force = true)
        patchEmbeddedMatePaths()
        executeCommand(
            "glib-compile-schemas ${prefixDir.absolutePath}/share/glib-2.0/schemas >/dev/null 2>&1 || true",
        )
        marker.writeText("ready")
    }

'''
insert_before(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    "    private fun refreshDesktopMenus() {\n",
    helpers,
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''    private fun refreshDesktopMenus() {
        executeCommand(
            "update-desktop-database ${prefixDir.absolutePath}/share/applications >/dev/null 2>&1 || true",
        )
    }
''',
    '''    private fun refreshDesktopMenus() {
        installDroidDeskBuiltIns()
        syncStoreDesktopLaunchers()
        executeCommand(
            "update-desktop-database ${prefixDir.absolutePath}/share/applications >/dev/null 2>&1 || true",
        )
        executeCommand(
            "update-desktop-database ${File(homeDir, ".local/share/applications").absolutePath} >/dev/null 2>&1 || true",
        )
    }
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        if (selectedDesktop == "xfce4") {
            XfceMobileProfile.install(
                context = context,
                homeDir = homeDir.apply { mkdirs() },
                wallpaperFile = File(
                    homeDir,
                    ".local/share/backgrounds/droiddesk-ubuntu-touch.jpg",
                ),
            )
            AndroidAppBridge.syncLaunchers(
                context = context,
                homeDir = homeDir,
                python = File(prefixDir, "bin/python3"),
            )
        }
''',
    '''        if (selectedDesktop == "xfce4") {
            XfceMobileProfile.install(
                context = context,
                homeDir = homeDir.apply { mkdirs() },
                wallpaperFile = File(
                    homeDir,
                    ".local/share/backgrounds/droiddesk-ubuntu-touch.jpg",
                ),
            )
        }
        if (selectedDesktop == "mate") {
            prepareMateV203()
        }
        AndroidAppBridge.syncLaunchers(
            context = context,
            homeDir = homeDir,
            python = File(prefixDir, "bin/python3"),
        )
        refreshDesktopMenus()
''',
)

prep = r'''
        val desktopPreparation = when (selectedDesktop) {
            "mate" -> """
                mkdir -p "${homeDir.absolutePath}/.config/droiddesk"
                if [ ! -f "${homeDir.absolutePath}/.config/droiddesk/mate-v203.done" ]; then
                    dconf reset -f /org/mate/panel/ >/dev/null 2>&1 || true
                    gsettings set org.mate.caja.desktop computer-icon-visible false >/dev/null 2>&1 || true
                    gsettings set org.mate.caja.desktop trash-icon-visible false >/dev/null 2>&1 || true
                    gsettings set org.mate.caja.desktop network-icon-visible false >/dev/null 2>&1 || true
                    gsettings set org.mate.caja.desktop home-icon-visible false >/dev/null 2>&1 || true
                    touch "${homeDir.absolutePath}/.config/droiddesk/mate-v203.done"
                fi
                mate-notification-daemon >/dev/null 2>&1 &
            """.trimIndent()
            else -> ""
        }

'''
insert_before(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '        val runScript = """\n',
    prep,
)
replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''            echo "DIAG: Launching ${'$'}desktopCommand natively on DISPLAY=:0 ..."
            exec ${'$'}desktopCommand
''',
    '''            ${'$'}desktopPreparation
            echo "DIAG: Launching ${'$'}desktopCommand natively on DISPLAY=:0 ..."
            exec ${'$'}desktopCommand
''',
)
replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        marker.writeText(selectedDesktop)
        onProgress?.invoke(1.0, "Native Linux setup complete")
''',
    '''        marker.writeText(selectedDesktop)
        refreshDesktopMenus()
        onProgress?.invoke(1.0, "Native Linux setup complete")
''',
)

print("Applied v2.0.3 Linux/MATE integration.")
