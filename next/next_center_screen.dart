import 'package:flutter/material.dart';
import 'package:droiddesk/services/platform_bridge.dart';
import 'package:droiddesk/theme/droid_theme.dart';

class NextCenterScreen extends StatefulWidget {
  const NextCenterScreen({super.key});

  @override
  State<NextCenterScreen> createState() => _NextCenterScreenState();
}

class _NextCenterScreenState extends State<NextCenterScreen> {
  Map<String, dynamic> _status = {};
  Map<String, dynamic> _guardian = {};
  bool _loading = true;
  String? _busy;
  String _message = '';

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        DroidDeskPlatform.getNextStatus(),
        DroidDeskPlatform.getGuardianReport(),
      ]);
      if (!mounted) return;
      setState(() {
        _status = results[0];
        _guardian = results[1];
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _message = 'Could not load DroidDesk Next: $e';
        _loading = false;
      });
    }
  }

  Future<void> _run(
    String id,
    Future<dynamic> Function() action, {
    String success = 'Completed',
  }) async {
    if (_busy != null) return;
    setState(() {
      _busy = id;
      _message = '';
    });
    try {
      final result = await action();
      if (!mounted) return;
      setState(() {
        _message = result is bool && !result ? 'Operation did not complete' : success;
      });
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      setState(() => _message = 'Failed: $e');
    } finally {
      if (mounted) setState(() => _busy = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final score = (_guardian['score'] as num?)?.toInt() ?? 0;
    final checks = ((_guardian['checks'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final distros = Map<String, dynamic>.from(_status['distros'] as Map? ?? {});
    final performance = _status['performanceMode']?.toString() ?? 'balanced';
    final memory = (_status['memoryLimitMB'] as num?)?.toInt() ?? 2048;

    return Scaffold(
      appBar: AppBar(
        title: const Text('DroidDesk Next'),
        actions: [
          IconButton(onPressed: _busy == null ? _refresh : null, icon: const Icon(Icons.refresh_rounded)),
        ],
      ),
      body: Container(
        decoration: BoxDecoration(gradient: DroidTheme.backgroundGradient),
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.fromLTRB(18, 16, 18, 36),
                children: [
                  _hero(score),
                  if (_message.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    _messageCard(_message),
                  ],
                  const SizedBox(height: 18),
                  _sectionTitle('GUARDIAN & RECOVERY'),
                  _panel([
                    for (final check in checks)
                      _statusRow(
                        check['label']?.toString() ?? 'Check',
                        check['detail']?.toString() ?? '',
                        check['ok'] == true,
                      ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _action('guardian', 'Scan', Icons.health_and_safety_rounded, _refresh),
                        _action(
                          'repair',
                          'One-Tap Repair',
                          Icons.build_circle_rounded,
                          () => _run('repair', DroidDeskPlatform.runGuardianRepair, success: 'Repair finished'),
                        ),
                        _action(
                          'safe',
                          'Safe Desktop',
                          Icons.shield_moon_rounded,
                          () => _run('safe', DroidDeskPlatform.startSafeDesktop, success: 'Safe desktop started'),
                        ),
                      ],
                    ),
                  ]),
                  const SizedBox(height: 18),
                  _sectionTitle('PERFORMANCE & MEMORY'),
                  _panel([
                    Text('Mode', style: DroidTheme.headingSm),
                    const SizedBox(height: 10),
                    SegmentedButton<String>(
                      segments: const [
                        ButtonSegment(value: 'battery', label: Text('Battery'), icon: Icon(Icons.battery_saver_rounded)),
                        ButtonSegment(value: 'balanced', label: Text('Balanced'), icon: Icon(Icons.tune_rounded)),
                        ButtonSegment(value: 'performance', label: Text('Performance'), icon: Icon(Icons.bolt_rounded)),
                      ],
                      selected: {performance},
                      onSelectionChanged: _busy != null
                          ? null
                          : (selection) {
                              _run(
                                'perf',
                                () => DroidDeskPlatform.setNextPerformance(selection.first, memory),
                                success: 'Performance profile saved',
                              );
                            },
                    ),
                    const SizedBox(height: 14),
                    Text('Linux RAM limit: $memory MB', style: DroidTheme.bodyMd),
                    Slider(
                      min: 768,
                      max: 8192,
                      divisions: 29,
                      value: memory.clamp(768, 8192).toDouble(),
                      label: '$memory MB',
                      onChanged: _busy != null
                          ? null
                          : (v) {
                              final next = ((v / 256).round() * 256).clamp(768, 8192);
                              setState(() => _status['memoryLimitMB'] = next);
                            },
                      onChangeEnd: _busy != null
                          ? null
                          : (v) {
                              final next = ((v / 256).round() * 256).clamp(768, 8192);
                              _run(
                                'memory',
                                () => DroidDeskPlatform.setNextPerformance(performance, next),
                                success: 'RAM limiter updated',
                              );
                            },
                    ),
                    _metricGrid(),
                  ]),
                  const SizedBox(height: 18),
                  _sectionTitle('DESKTOPS, DISPLAYS & PRESETS'),
                  _panel([
                    Text('Desktop environments', style: DroidTheme.headingSm),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final de in ['xfce4', 'mate', 'lxqt', 'kde'])
                          _action(
                            'de-$de',
                            de.toUpperCase(),
                            Icons.desktop_windows_rounded,
                            () => _run(
                              'de-$de',
                              () => DroidDeskPlatform.installNextDesktop(de),
                              success: '${de.toUpperCase()} ready',
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Text('Launch resolution', style: DroidTheme.headingSm),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _action('720', '1280×720', Icons.phone_android_rounded, () => DroidDeskPlatform.startLinux(width: 1280, height: 720)),
                        _action('1080', '1920×1080', Icons.monitor_rounded, () => DroidDeskPlatform.startLinux(width: 1920, height: 1080)),
                        _action('1440', '2560×1440', Icons.desktop_mac_rounded, () => DroidDeskPlatform.startLinux(width: 2560, height: 1440)),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Text(
                      'External displays detected: ${_status['externalDisplays'] ?? 0}',
                      style: DroidTheme.bodyMd,
                    ),
                    const SizedBox(height: 14),
                    Text('Workspace presets', style: DroidTheme.headingSm),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final preset in const {
                          'general': 'General',
                          'coding': 'Coding',
                          'school': 'School',
                          'creative': 'Creative',
                          'security': 'Security',
                          'lightweight': 'Lightweight',
                        }.entries)
                          _action(
                            'preset-${preset.key}',
                            preset.value,
                            Icons.dashboard_customize_rounded,
                            () => _run(
                              'preset-${preset.key}',
                              () => DroidDeskPlatform.applyNextPreset(preset.key),
                              success: '${preset.value} preset installed',
                            ),
                          ),
                      ],
                    ),
                  ]),
                  const SizedBox(height: 18),
                  _sectionTitle('FILES, STORAGE & BACKUPS'),
                  _panel([
                    _statusRow('Shared Android folders', 'Downloads · Documents · Pictures · Camera · Projects', _status['sharedFolders'] == true),
                    _statusRow('All-files permission', 'Required for unrestricted shared-folder links', _status['allFilesAccess'] == true),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _action(
                          'shares',
                          'Connect Folders',
                          Icons.folder_shared_rounded,
                          () => _run('shares', DroidDeskPlatform.configureNextSharedFolders, success: 'Shared folders configured'),
                        ),
                        _action(
                          'storageSettings',
                          'Storage Access',
                          Icons.admin_panel_settings_rounded,
                          () => DroidDeskPlatform.openAndroidControl('storage'),
                        ),
                        _action(
                          'clean',
                          'Clean Caches',
                          Icons.cleaning_services_rounded,
                          () => _run('clean', DroidDeskPlatform.cleanNextCaches, success: 'Caches cleaned'),
                        ),
                        _action(
                          'snapshot',
                          'Create Snapshot',
                          Icons.restore_rounded,
                          () => _run('snapshot', DroidDeskPlatform.createRecoveryPoint, success: 'Recovery snapshot created'),
                        ),
                        _action(
                          'export',
                          'Export Backup',
                          Icons.file_upload_rounded,
                          () => _run('export', DroidDeskPlatform.exportNextSnapshot, success: 'Latest backup exported'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text('Snapshots: ${_status['snapshotCount'] ?? 0}', style: DroidTheme.bodyMd),
                  ]),
                  const SizedBox(height: 18),
                  _sectionTitle('NETWORK & FALLBACK'),
                  _panel([
                    _statusRow('SSH server', '${_status['localIp'] ?? '127.0.0.1'}:8022', _status['sshRunning'] == true),
                    _statusRow('VNC fallback', '127.0.0.1:5901 · local-only', _status['vncRunning'] == true),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _action(
                          'ssh',
                          _status['sshRunning'] == true ? 'Stop SSH' : 'Start SSH',
                          Icons.lan_rounded,
                          () => _run(
                            'ssh',
                            () => DroidDeskPlatform.toggleNextSsh(_status['sshRunning'] != true),
                            success: 'SSH state updated',
                          ),
                        ),
                        _action(
                          'vnc',
                          _status['vncRunning'] == true ? 'Stop VNC' : 'Start VNC',
                          Icons.cast_connected_rounded,
                          () => _run(
                            'vnc',
                            () => DroidDeskPlatform.toggleNextVnc(_status['vncRunning'] != true),
                            success: 'VNC fallback state updated',
                          ),
                        ),
                      ],
                    ),
                  ]),
                  const SizedBox(height: 18),
                  _sectionTitle('ANDROID ↔ LINUX BRIDGES'),
                  _panel([
                    _statusRow('Text clipboard', 'Automatic foreground sync', _status['clipboardBridge'] == true),
                    _statusRow('Audio + microphone', 'PulseAudio Android backend', _status['audioBridge'] == true),
                    _statusRow('Linux → Android notifications', 'droiddesk-notify-android', _status['notificationBridge'] == true),
                    _statusRow('Android → Linux notifications', 'Requires Android Notification Access', _status['notificationAccess'] == true),
                    _statusRow('Camera bridge', 'Android/DCIM/Camera shared into Linux', _status['cameraBridge'] == true),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _action(
                          'notify',
                          'Notification Access',
                          Icons.notifications_active_rounded,
                          () => DroidDeskPlatform.openAndroidControl('notification_access'),
                        ),
                        _action(
                          'camera',
                          'Connect Camera Folder',
                          Icons.camera_alt_rounded,
                          () => DroidDeskPlatform.configureNextSharedFolders(),
                        ),
                      ],
                    ),
                  ]),
                  const SizedBox(height: 18),
                  _sectionTitle('DISTROS & DEVELOPMENT'),
                  _panel([
                    for (final id in ['debian', 'ubuntu', 'alpine'])
                      _statusRow(
                        '${id[0].toUpperCase()}${id.substring(1)} container',
                        'PRoot distro profile',
                        distros[id] == true,
                      ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final id in ['debian', 'ubuntu', 'alpine'])
                          _action(
                            'distro-$id',
                            'Install ${id[0].toUpperCase()}${id.substring(1)}',
                            Icons.inventory_2_rounded,
                            () => _run(
                              'distro-$id',
                              () => DroidDeskPlatform.installNextDistro(id),
                              success: '$id container ready',
                            ),
                          ),
                        _action(
                          'dev',
                          'Developer Pack',
                          Icons.code_rounded,
                          () => _run('dev', DroidDeskPlatform.installNextDevPack, success: 'Developer tools installed'),
                        ),
                      ],
                    ),
                  ]),
                  const SizedBox(height: 18),
                  _sectionTitle('DIAGNOSTICS'),
                  _panel([
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _action('processes', 'Processes', Icons.account_tree_rounded, _showProcesses),
                        _action('logs', 'Guardian Logs', Icons.article_rounded, _showLogs),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Persistent sessions, Android app launchers, package search/install/remove, GPU auto-detection, snapshots, clipboard sync, audio, and desktop input controls remain active from the existing DroidDesk foundation.',
                      style: DroidTheme.bodySm,
                    ),
                  ]),
                ],
              ),
      ),
    );
  }

  Widget _hero(int score) {
    final color = score >= 90 ? DroidTheme.success : score >= 70 ? DroidTheme.warning : DroidTheme.error;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: DroidTheme.primaryGradient,
        borderRadius: BorderRadius.circular(DroidTheme.radiusLg),
      ),
      child: Row(
        children: [
          const Icon(Icons.shield_rounded, color: Colors.white, size: 44),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('DroidDesk Guardian', style: DroidTheme.headingLg.copyWith(color: Colors.white)),
                Text('Health score $score%', style: DroidTheme.bodyMd.copyWith(color: Colors.white70)),
              ],
            ),
          ),
          CircleAvatar(
            backgroundColor: Colors.white,
            child: Text('$score', style: TextStyle(color: color, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _metricGrid() {
    final values = [
      ('RAM free', '${_status['availableRamMB'] ?? '?'} MB'),
      ('Linux', '${_status['linuxSizeMB'] ?? '?'} MB'),
      ('Home', '${_status['homeSizeMB'] ?? '?'} MB'),
      ('Storage', '${_status['storageFreeMB'] ?? '?'} MB free'),
      ('GPU', _status['graphicsMode']?.toString() ?? 'Automatic'),
      ('Desktop', _status['installedDE']?.toString().toUpperCase() ?? 'None'),
    ];
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: values
          .map(
            (v) => Container(
              width: 150,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: DroidTheme.cardBg,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: DroidTheme.surfaceBorder),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(v.$1, style: DroidTheme.bodySm),
                  Text(v.$2, style: DroidTheme.monoSm),
                ],
              ),
            ),
          )
          .toList(),
    );
  }

  Widget _sectionTitle(String text) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(text, style: DroidTheme.label),
      );

  Widget _panel(List<Widget> children) => Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: DroidTheme.cardBg,
          borderRadius: BorderRadius.circular(DroidTheme.radiusMd),
          border: Border.all(color: DroidTheme.surfaceBorder),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: children),
      );

  Widget _statusRow(String title, String subtitle, bool ok) => ListTile(
        dense: true,
        contentPadding: EdgeInsets.zero,
        leading: Icon(
          ok ? Icons.check_circle_rounded : Icons.error_outline_rounded,
          color: ok ? DroidTheme.success : DroidTheme.warning,
        ),
        title: Text(title, style: DroidTheme.headingSm),
        subtitle: Text(subtitle, style: DroidTheme.bodySm),
      );

  Widget _action(String id, String label, IconData icon, Future<dynamic> Function() onTap) {
    final busy = _busy == id;
    return OutlinedButton.icon(
      onPressed: _busy != null
          ? null
          : () async {
              setState(() => _busy = id);
              try {
                await onTap();
                await _refresh();
              } finally {
                if (mounted) setState(() => _busy = null);
              }
            },
      icon: busy
          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
          : Icon(icon, size: 18),
      label: Text(label),
    );
  }

  Widget _messageCard(String text) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: DroidTheme.surface,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: DroidTheme.surfaceBorder),
        ),
        child: Text(text, style: DroidTheme.bodySm),
      );

  Future<void> _showProcesses() async {
    final text = await DroidDeskPlatform.getNextProcesses();
    if (!mounted) return;
    await _showText('Linux Processes', text);
  }

  Future<void> _showLogs() async {
    final text = await DroidDeskPlatform.getNextLogs();
    if (!mounted) return;
    await _showText('Guardian Logs', text);
  }

  Future<void> _showText(String title, String text) async {
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: SizedBox(
          width: double.maxFinite,
          child: SingleChildScrollView(
            child: SelectableText(text, style: DroidTheme.monoSm),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close')),
        ],
      ),
    );
  }
}
