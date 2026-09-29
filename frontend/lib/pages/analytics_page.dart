import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import '../services/content_job_service.dart';

class AnalyticsPage extends StatefulWidget {
  const AnalyticsPage({super.key});

  @override
  State<AnalyticsPage> createState() => _AnalyticsPageState();
}

class _AnalyticsPageState extends State<AnalyticsPage> {
  final ContentJobService _service = ContentJobService();
  ContentAnalyticsSummary? _summary;
  List<AnalyticsProviderCapability> _providers = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final summary = await _service.getAnalyticsSummary();
      List<AnalyticsProviderCapability> providers = const [];
      try {
        providers = await _service.getAnalyticsProviders();
      } catch (_) {
        // Provider availability must not hide stored analytics.
      }
      if (!mounted) return;
      setState(() {
        _summary = summary;
        _providers = providers;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  String _duration(double? seconds) {
    if (seconds == null) return '—';
    if (seconds < 60) return '${seconds.round()}s';
    if (seconds < 3600) return '${(seconds / 60).toStringAsFixed(1)}m';
    if (seconds < 86400) return '${(seconds / 3600).toStringAsFixed(1)}h';
    return '${(seconds / 86400).toStringAsFixed(1)}d';
  }

  @override
  Widget build(BuildContext context) {
    final summary = _summary;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Performance'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(_error!, textAlign: TextAlign.center),
                  ),
                )
              : summary == null
                  ? const Center(child: Text('No analytics data.'))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView(
                        padding: const EdgeInsets.all(12),
                        children: [
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              _MetricCard(label: 'Jobs', value: '${summary.jobsTotal}'),
                              _MetricCard(label: 'Published', value: '${summary.published}'),
                              _MetricCard(label: 'Review', value: '${summary.review}'),
                              _MetricCard(label: 'Failed', value: '${summary.failed}'),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Card(
                            child: Padding(
                              padding: const EdgeInsets.all(14),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'Pipeline timing',
                                    style: TextStyle(
                                      fontWeight: FontWeight.w900,
                                      color: AshColors.boneWhite,
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                  _MetricRow(
                                    label: 'Average MiniBoss score',
                                    value: summary.averageScore?.toStringAsFixed(1) ?? '—',
                                  ),
                                  _MetricRow(
                                    label: 'Average generation time',
                                    value: _duration(summary.averageGenerationSeconds),
                                  ),
                                  _MetricRow(
                                    label: 'Average time to publish',
                                    value: _duration(summary.averageTimeToPublishSeconds),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              _MetricCard(
                                label: 'Views',
                                value: '${summary.totalViews}',
                              ),
                              _MetricCard(
                                label: 'Interactions',
                                value: '${summary.totalInteractions}',
                              ),
                              _MetricCard(
                                label: 'Engagement',
                                value: summary.engagementRatePercent == null
                                    ? '—'
                                    : '${summary.engagementRatePercent!.toStringAsFixed(2)}%',
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Card(
                            child: Padding(
                              padding: const EdgeInsets.all(14),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'Publishing performance',
                                    style: TextStyle(
                                      fontWeight: FontWeight.w900,
                                      color: AshColors.boneWhite,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    summary.performanceAvailable
                                        ? '${summary.performanceSnapshots} snapshots · ${summary.latestSeries} current platform series.'
                                        : 'No performance snapshots yet. Import real platform metrics when available; SoloForge will not fabricate engagement values.',
                                    style: const TextStyle(
                                      color: AshColors.smokeSilver,
                                      height: 1.4,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Card(
                            child: Padding(
                              padding: const EdgeInsets.all(14),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'Analytics providers',
                                    style: TextStyle(
                                      fontWeight: FontWeight.w900,
                                      color: AshColors.boneWhite,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  if (_providers.isEmpty)
                                    const Text(
                                      'No connected publishing providers.',
                                      style: TextStyle(color: AshColors.smokeSilver),
                                    )
                                  else
                                    ..._providers.map(
                                      (provider) => _ProviderRow(provider: provider),
                                    ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          _BreakdownCard(
                            title: 'Jobs by platform',
                            values: summary.byPlatform,
                          ),
                          const SizedBox(height: 10),
                          _BreakdownCard(
                            title: 'Jobs by status',
                            values: summary.byStatus,
                          ),
                        ],
                      ),
                    ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 150,
      child: Card(
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: const TextStyle(color: AshColors.smokeSilver)),
              const SizedBox(height: 6),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w900,
                  color: AshColors.boneWhite,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Expanded(
            child: Text(label, style: const TextStyle(color: AshColors.smokeSilver)),
          ),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }
}

class _BreakdownCard extends StatelessWidget {
  const _BreakdownCard({required this.title, required this.values});

  final String title;
  final Map<String, int> values;

  @override
  Widget build(BuildContext context) {
    final entries = values.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.w900,
                color: AshColors.boneWhite,
              ),
            ),
            const SizedBox(height: 8),
            if (entries.isEmpty)
              const Text('No data.', style: TextStyle(color: AshColors.smokeSilver))
            else
              ...entries.map(
                (entry) => _MetricRow(
                  label: entry.key.replaceAll('_', ' '),
                  value: '${entry.value}',
                ),
              ),
          ],
        ),
      ),
    );
  }
}


class _ProviderRow extends StatelessWidget {
  const _ProviderRow({required this.provider});

  final AnalyticsProviderCapability provider;

  @override
  Widget build(BuildContext context) {
    final metrics = provider.engagementMetrics == true
        ? 'Metrics supported'
        : provider.engagementMetrics == false
            ? 'Metadata only'
            : 'Metrics capability unknown';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              '${provider.platform} · ${provider.username}',
              style: const TextStyle(color: AshColors.smokeSilver),
            ),
          ),
          Text(
            metrics,
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }
}
