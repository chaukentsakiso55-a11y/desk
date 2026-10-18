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

def replace_all(path, replacements):
    p = root / path
    text = p.read_text(encoding="utf-8")
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f"Expected text not found in {path}: {old}")
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")

replace_once(
    "app/pubspec.yaml",
    "version: 1.0.3+103\n",
    "version: 0.1.0+100\n",
)

replace_once(
    "app/android/app/build.gradle.kts",
    'applicationId = "com.orailnoor.droiddesk"',
    'applicationId = "com.cyberpulse.obsidian"',
)

replace_all(
    "app/android/app/src/main/AndroidManifest.xml",
    [
        ('android:label="DroidDesk"', 'android:label="OBSIDIAN"'),
        ('android:name=".MainActivity"', 'android:name="com.orailnoor.droiddesk.MainActivity"'),
        ('android:name=".view.DesktopActivity"', 'android:name="com.orailnoor.droiddesk.view.DesktopActivity"'),
        ('android:name=".x11.X11ServerService"', 'android:name="com.orailnoor.droiddesk.x11.X11ServerService"'),
        ('android:name=".service.DroidDeskService"', 'android:name="com.orailnoor.droiddesk.service.DroidDeskService"'),
    ],
)

replace_once(
    "app/lib/main.dart",
    "title: 'DroidDesk',",
    "title: 'OBSIDIAN',",
)

replace_all(
    "app/lib/screens/welcome_screen.dart",
    [
        ("Premium, animated landing with the DroidDesk brand.", "Obsidian secure desktop welcome experience."),
        ("'DroidDesk'", "'OBSIDIAN'"),
        ("'Full Linux Desktop on Android'", "'Private AI Security Desktop on Android'"),
        ("'Ubuntu · XFCE Desktop · Single App'", "'LOCAL CORE · X11 · SECURITY WORKSPACE'"),
        ("'Containerized'", "'Private Core'"),
        ("'Root Optional'", "'Root Aware'"),
        ("'Linux Desktop'", "'Secure Desktop'"),
        ("'Local Execution'", "'Local First'"),
        ("'Set Up Desktop Essentials'", "'Initialize Obsidian'"),
    ],
)

replace_all(
    "app/lib/theme/droid_theme.dart",
    [
        ("Color(0xFF0A0E17)", "Color(0xFF05070D)"),
        ("Color(0xFF111827)", "Color(0xFF0B1020)"),
        ("Color(0xFF1A2332)", "Color(0xFF141A2E)"),
        ("Color(0xFF1E293B)", "Color(0xFF252C47)"),
        ("Color(0xFF151D2B)", "Color(0xFF0E1426)"),
        ("Color(0xFF6366F1)", "Color(0xFF7C3AED)"),
        ("Color(0xFF818CF8)", "Color(0xFFA78BFA)"),
    ],
)

home_path = root / "app/lib/screens/home_screen.dart"
home = home_path.read_text(encoding="utf-8")
home = home.replace(
    "import 'package:droiddesk/screens/desktop_tools_screen.dart';",
    "import 'package:droiddesk/screens/desktop_tools_screen.dart';\nimport 'package:droiddesk/screens/obsidian_security_screen.dart';",
)
for old, new in [
    ("Text('DroidDesk', style: DroidTheme.headingSm)", "Text('OBSIDIAN', style: DroidTheme.headingSm)"),
    ("'Desktop Running'", "'Obsidian Running'"),
    ("'Ready'", "'Core Ready'"),
    ("'Return to Desktop'", "'Return to Obsidian'"),
    ("'Launch Desktop'", "'Enter Obsidian'"),
    ("'Shutdown Linux environment'", "'Stop Obsidian runtime'"),
    ("'Start ${state.selectedDE.toUpperCase()} desktop environment'", "'Start the Obsidian desktop environment'"),
    ("title: 'Terminal',", "title: 'Obsidian Terminal',"),
    ("'Open a Linux shell in the ${state.hasRoot ? 'Ubuntu chroot' : 'native Termux'} environment'", "'Open the local Obsidian command environment'"),
    ("title: 'Add applications',", "title: 'Obsidian App Center',"),
    ("'Install applications or optional Debian compatibility'", "'Install desktop tools and compatibility packages'"),
    ("'SYSTEM'", "'OBSIDIAN CORE'"),
    ("title: const Text('Desktop Tools'),", "title: const Text('Obsidian Desktop Tools'),"),
    ("title: const Text('Reinstall Linux'),", "title: const Text('Rebuild Obsidian Core'),"),
    ("subtitle: const Text('Re-download and set up rootfs'),", "subtitle: const Text('Recreate the local Linux compatibility core'),"),
    ("'DroidDesk will stop opening automatically as your Home app. Android will ask you to choose another launcher.'", "'OBSIDIAN will stop opening automatically as your Home app. Android will ask you to choose another launcher.'"),
    ("return 'Ubuntu 24.04';", "return 'Obsidian Core · Ubuntu';"),
    ("return 'Termux';", "return 'Obsidian Core · Native';"),
]:
    if old not in home:
        raise SystemExit(f"Expected home text not found: {old}")
    home = home.replace(old, new)

anchor = """                      // ── Terminal ──
                      _ActionCard(
"""
if anchor not in home:
    raise SystemExit("Home action insertion point not found")
security_card = """                      _ActionCard(
                        icon: Icons.shield_rounded,
                        title: 'Obsidian Security Center',
                        subtitle:
                            'Inspect runtime isolation, device state, and privacy posture',
                        color: DroidTheme.accent,
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => const ObsidianSecurityScreen(),
                            ),
                          );
                        },
                      ),

                      const SizedBox(height: 10),

"""
home = home.replace(anchor, security_card + anchor, 1)
home_path.write_text(home, encoding="utf-8")

catalog = root / "app/lib/screens/apps/app_catalog_screen.dart"
catalog_text = catalog.read_text(encoding="utf-8")
catalog_text = catalog_text.replace("Applications", "Obsidian App Center")
catalog_text = catalog_text.replace("Search packages", "Search Obsidian packages")
catalog.write_text(catalog_text, encoding="utf-8")

replace_all(
    "app/lib/screens/desktop_tools_screen.dart",
    [
        ("title: const Text('Desktop Tools')", "title: const Text('Obsidian Desktop Tools')"),
        ("'The Linux session will stop. Current home files and settings will be replaced, and missing packages will be restored.'", "'The Obsidian session will stop. Current workspace files and settings will be replaced, and missing packages will be restored.'"),
    ],
)

replace_all(
    "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/XfceMobileProfile.kt",
    [
        ('private const val PROFILE_MARKER = ".droiddesk-xfce-mobile-v5"', 'private const val PROFILE_MARKER = ".obsidian-xfce-mobile-v1"'),
        ('name = "Terminal"', 'name = "Obsidian Terminal"'),
        ('comment = "Open the Linux terminal"', 'comment = "Open the Obsidian command environment"'),
        ('Log.i(TAG, "Installed Ubuntu-inspired XFCE mobile profile in ${homeDir.absolutePath}")', 'Log.i(TAG, "Installed Obsidian XFCE profile in ${homeDir.absolutePath}")'),
    ],
)

security = root / "app/lib/screens/obsidian_security_screen.dart"
security.write_text("""import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:droiddesk/state/app_state.dart';
import 'package:droiddesk/theme/droid_theme.dart';

class ObsidianSecurityScreen extends StatelessWidget {
  const ObsidianSecurityScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final device = state.deviceInfo;
    final runtimeMode = state.hasRoot ? 'Elevated chroot' : 'Android app sandbox';
    final runtimeStatus = state.isRunning ? 'Active' : 'Standby';
    final deviceName =
        '${device['brand'] ?? ''} ${device['model'] ?? ''}'.trim();

    return Scaffold(
      appBar: AppBar(title: const Text('Obsidian Security Center')),
      body: Container(
        decoration: BoxDecoration(gradient: DroidTheme.backgroundGradient),
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            _hero(runtimeStatus),
            const SizedBox(height: 16),
            _status(
              Icons.shield_outlined,
              'Runtime isolation',
              runtimeMode,
              state.hasRoot ? DroidTheme.warning : DroidTheme.success,
            ),
            _status(
              Icons.memory_rounded,
              'Obsidian core',
              runtimeStatus,
              state.isRunning ? DroidTheme.success : DroidTheme.textMuted,
            ),
            _status(
              Icons.storage_rounded,
              'Workspace storage',
              'App-private local storage',
              DroidTheme.secondary,
            ),
            _status(
              Icons.desktop_windows_rounded,
              'Desktop engine',
              state.selectedDE.toUpperCase(),
              DroidTheme.primaryLight,
            ),
            _status(
              Icons.phone_android_rounded,
              'Android host',
              deviceName.isEmpty ? 'Detected' : deviceName,
              DroidTheme.secondary,
            ),
            _status(
              Icons.visibility_off_rounded,
              'Privacy mode',
              'Local-first runtime',
              DroidTheme.success,
            ),
            const SizedBox(height: 18),
            Text('OBSIDIAN FOUNDATION', style: DroidTheme.label),
            const SizedBox(height: 8),
            Text(
              'Linux remains underneath for app and desktop compatibility while Obsidian owns the visible workspace, security controls, and Android bridge.',
              style: DroidTheme.bodyMd,
            ),
          ],
        ),
      ),
    );
  }

  Widget _hero(String status) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: DroidTheme.primaryGradient,
        borderRadius: BorderRadius.circular(DroidTheme.radiusLg),
      ),
      child: Row(
        children: [
          const Icon(Icons.security_rounded, color: Colors.white, size: 42),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'OBSIDIAN',
                  style: DroidTheme.headingLg.copyWith(color: Colors.white),
                ),
                Text(
                  'Security core · $status',
                  style: DroidTheme.bodySm.copyWith(color: Colors.white70),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _status(
    IconData icon,
    String title,
    String value,
    Color color,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: DroidTheme.cardBg,
        borderRadius: BorderRadius.circular(DroidTheme.radiusMd),
        border: Border.all(color: color.withValues(alpha: .28)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: DroidTheme.headingSm),
                Text(value, style: DroidTheme.bodySm),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
""", encoding="utf-8")

print("Applied Obsidian edition layer.")
