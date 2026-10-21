from pathlib import Path
import re
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

def regex_once(path, pattern, replacement):
    p = root / path
    text = p.read_text(encoding="utf-8")
    new, count = re.subn(pattern, lambda _match: replacement, text, count=1, flags=re.MULTILINE | re.DOTALL)
    if count != 1:
        raise SystemExit(f"Expected one regex match in {path}, found {count}")
    p.write_text(new, encoding="utf-8")

replace_once(
    "app/pubspec.yaml",
    "version: 2.0.1+201\n",
    "version: 2.0.2+202\n",
)

repo_block = r'''    private fun writeCoreRepositorySources(useCloudflare: Boolean) {
        val mainHost = if (useCloudflare) "packages-cf.termux.dev" else "packages.termux.dev"
        val aptDir = File(prefixDir, "etc/apt")
        val sourcesDir = File(aptDir, "sources.list.d")
        aptDir.mkdirs()
        sourcesDir.mkdirs()

        File(aptDir, "sources.list").writeText(
            "deb https://$mainHost/apt/termux-main stable main\n",
        )
        File(sourcesDir, "x11.list").writeText(
            "deb https://$mainHost/apt/termux-x11 x11 main\n",
        )

        File(sourcesDir, "tur.list").delete()
    }

    private fun refreshCorePackageLists(
        onProgress: ((Double, String) -> Unit)? = null,
    ): Boolean {
        val attempts = listOf(
            false to "official Termux mirror",
            true to "Termux Cloudflare fallback",
        )

        for ((useCloudflare, label) in attempts) {
            if (packageOperationCancelled) return false
            onProgress?.invoke(0.20, "Refreshing package indexes from $label...")
            writeCoreRepositorySources(useCloudflare)

            val listsDir = File(prefixDir, "var/lib/apt/lists")
            listsDir.listFiles()?.forEach { entry ->
                if (entry.name != "partial" && entry.name != "lock") {
                    entry.deleteRecursively()
                }
            }
            File(listsDir, "partial").mkdirs()

            val output = executeCommand(
                "timeout --signal=TERM --kill-after=5s 150s " +
                    "apt-get -o Acquire::Retries=3 " +
                    "-o Acquire::http::Timeout=25 " +
                    "-o Acquire::https::Timeout=25 update",
            )
            if (packageOperationCancelled) return false

            val mainList = File(prefixDir, "var/lib/apt/lists").listFiles()
                ?.any { it.name.contains("termux-main") && it.name.endsWith("_Packages") } == true
            val x11List = File(prefixDir, "var/lib/apt/lists").listFiles()
                ?.any { it.name.contains("termux-x11") && it.name.endsWith("_Packages") } == true

            if (!output.startsWith("Error:") && mainList && x11List) {
                Log.i(TAG, "Package indexes refreshed successfully using $label")
                return true
            }
            Log.w(TAG, "Package index refresh failed using $label")
        }

        return false
    }

    private fun installRepoPackages(
        onProgress: ((Double, String) -> Unit)? = null,
    ): Boolean {
        val pkgs = listOf("x11-repo")

        val aptDir = File(prefixDir, "etc/apt")
        val sourcesDir = File(aptDir, "sources.list.d")
        aptDir.mkdirs()
        sourcesDir.mkdirs()
        File(sourcesDir, "x11.list").delete()
        File(sourcesDir, "tur.list").delete()

        File(aptDir, "sources.list").writeText(
            "deb https://packages.termux.dev/apt/termux-main stable main\\n",
        )
        val firstUpdate = executeCommand(
            "timeout --signal=TERM --kill-after=5s 120s " +
                "apt-get -o Acquire::Retries=3 update",
        )
        if (firstUpdate.startsWith("Error:")) {
            File(aptDir, "sources.list").writeText(
                "deb https://packages-cf.termux.dev/apt/termux-main stable main\\n",
            )
            val fallback = executeCommand(
                "timeout --signal=TERM --kill-after=5s 120s " +
                    "apt-get -o Acquire::Retries=3 update",
            )
            if (fallback.startsWith("Error:")) {
                Log.e(TAG, "Both Termux main mirrors failed before x11-repo setup")
                return false
            }
        }

        val downloadCmd =
            "cd \"${prefixDir.absolutePath}\" && apt-get download x11-repo"
        if (executeCommand(downloadCmd).startsWith("Error:")) {
            Log.e(TAG, "Failed to download x11-repo")
            return false
        }

        if (executeCommand("dpkg --unpack x11-repo_*.deb").startsWith("Error:")) {
            Log.e(TAG, "Failed to unpack x11-repo")
            return false
        }

        val postinst = File(prefixDir, "var/lib/dpkg/info/x11-repo.postinst")
        postinst.writeText("#!/system/bin/sh\nexit 0\n")
        postinst.setExecutable(true, false)

        if (executeCommand("dpkg --configure x11-repo").startsWith("Error:")) {
            Log.e(TAG, "Failed to configure x11-repo")
            return false
        }

        return refreshCorePackageLists(onProgress)
    }

    private fun ensureTurRepository(): Boolean {
        val sources = File(prefixDir, "etc/apt/sources.list.d/tur.list")
        if (sources.isFile && sources.readText().contains("tur.kcubeterm.com")) {
            val update = executeCommand(
                "timeout --signal=TERM --kill-after=5s 90s " +
                    "apt-get -o Acquire::Retries=2 update",
            )
            return !update.startsWith("Error:")
        }

        val output = executeCommand(
            "DEBIAN_FRONTEND=noninteractive apt-get install -y tur-repo",
        )
        if (output.startsWith("Error:")) return false
        patchShebangs(force = true)

        val postinst = File(prefixDir, "var/lib/dpkg/info/tur-repo.postinst")
        if (postinst.exists()) {
            postinst.writeText("#!/system/bin/sh\nexit 0\n")
            postinst.setExecutable(true, false)
        }
        executeCommand("dpkg --configure tur-repo")

        val update = executeCommand(
            "timeout --signal=TERM --kill-after=5s 90s " +
                "apt-get -o Acquire::Retries=2 update",
        )
        return !update.startsWith("Error:")
    }

'''
regex_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    r'''    private fun installRepoPackages\(\): Boolean \{.*?^    \}\n\n    private fun installPackageGroup''',
    repo_block + "    private fun installPackageGroup",
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        if (!installRepoPackages()) {
            Log.e(TAG, "Failed to install x11-repo/tur-repo")
            return false
        }
        onProgress?.invoke(0.24, "Updating native package database...")

        // Finish configuring anything left over from a previous run, then install
        // the desktop, GPU drivers, and build tools. Each install is followed by a
        // shebang patch + configure pass so postinst scripts find our prefix.
        if (!installPackageGroup("dpkg --configure -a")) {
            Log.e(TAG, "Initial dpkg --configure -a failed")
            return false
        }
        if (!installPackageGroup("pkg update -y")) {
            Log.e(TAG, "pkg update failed")
            return false
        }
''',
    '''        if (!installRepoPackages(onProgress)) {
            Log.e(TAG, "Failed to configure resilient Termux main/X11 repositories")
            return false
        }
        onProgress?.invoke(0.24, "Package indexes verified")

        if (!installPackageGroup("dpkg --configure -a")) {
            Log.e(TAG, "Initial dpkg --configure -a failed")
            return false
        }
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        if (appId == "nodejs" || appId == "code_oss") {
            onProgress?.invoke(0.08, "Preparing relocated Node.js dependency...")
            if (!isDpkgPackageInstalled("nodejs") && !installRelocatedNodejs()) return false
        }
''',
    '''        if (appId == "code_oss") {
            onProgress?.invoke(0.05, "Preparing optional TUR application repository...")
            if (!ensureTurRepository()) {
                onProgress?.invoke(-1.0, "TUR repository is unavailable. Core Linux remains usable.")
                return false
            }
        }

        if (appId == "nodejs" || appId == "code_oss") {
            onProgress?.invoke(0.08, "Preparing relocated Node.js dependency...")
            if (!isDpkgPackageInstalled("nodejs") && !installRelocatedNodejs()) return false
        }
''',
)

replace_once(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt",
    '''        val queryOutput = executeCommand("dpkg-query -W $requestedPackages")
        val recovered = !queryOutput.startsWith("Error:")
        if (recovered) {
            Log.i(TAG, "Package group recovered after shebang patching: $requestedPackages")
        }
        return recovered
''',
    '''        val queryOutput = executeCommand("dpkg-query -W $requestedPackages")
        val recovered = !queryOutput.startsWith("Error:")
        if (recovered) {
            Log.i(TAG, "Package group recovered after shebang patching: $requestedPackages")
            return true
        }

        if (!refreshCorePackageLists()) return false
        val retryOutput = executeCommand(
            "DEBIAN_FRONTEND=noninteractive apt-get " +
                "-o Dpkg::Options::=--force-confdef " +
                "-o Dpkg::Options::=--force-confold install -y $requestedPackages",
        )
        patchShebangs(force = true)
        executeCommand(
            "timeout --signal=TERM --kill-after=5s 90s dpkg --configure -a",
        )
        val retryQuery = executeCommand("dpkg-query -W $requestedPackages")
        return !retryOutput.startsWith("Error:") && !retryQuery.startsWith("Error:")
''',
)

print("Applied DroidDesk Next v2.0.2 repository resilience fixes.")
