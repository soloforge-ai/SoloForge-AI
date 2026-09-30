import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import '../models/content_job.dart';
import '../services/content_job_service.dart';
import '../widgets/home/hero_banner.dart';
import 'about_page.dart';
import 'analytics_page.dart';
import 'asset_forge_page.dart';
import 'content_job_page.dart';
import 'settings_page.dart';

enum QueueFilter { all, today, review, blocked, published }

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final ContentJobService _contentJobService = ContentJobService();
  final TextEditingController _ideaController = TextEditingController();

  List<ContentJob> _allJobs = const [];
  List<ContentJob> _jobs = const [];
  QueueFilter _filter = QueueFilter.all;
  String _keyword = '';
  bool _loading = true;
  bool _ideaBusy = false;
  IdeaAnalysis? _ideaAnalysis;
  String? _ideaError;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadJobs();
  }

  @override
  void dispose() {
    _ideaController.dispose();
    super.dispose();
  }

  Future<void> _analyzeIdea() async {
    final idea = _ideaController.text.trim();
    if (idea.length < 3 || _ideaBusy) return;
    setState(() {
      _ideaBusy = true;
      _ideaError = null;
      _ideaAnalysis = null;
    });
    try {
      final analysis = await _contentJobService.analyzeIdea(idea);
      if (!mounted) return;
      setState(() => _ideaAnalysis = analysis);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _ideaError = error.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) setState(() => _ideaBusy = false);
    }
  }

  Future<void> _createIdeaJob(
    IdeaRecommendation recommendation, {
    required bool generateNow,
  }) async {
    if (_ideaBusy) return;
    setState(() {
      _ideaBusy = true;
      _ideaError = null;
    });
    try {
      final job = await _contentJobService.createFromIdea(
        idea: _ideaController.text.trim(),
        recommendationId: recommendation.id,
        generateNow: generateNow,
      );
      if (!mounted) return;
      setState(() {
        _ideaController.clear();
        _ideaAnalysis = null;
      });
      await _loadJobs();
      if (!mounted) return;
      if (generateNow) {
        await _openJob(job);
      }
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _ideaError = error.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) setState(() => _ideaBusy = false);
    }
  }

  Future<void> _loadJobs() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final jobs = await _contentJobService.getJobs();
      if (!mounted) return;
      _allJobs = jobs;
      _applyFilters();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  void _applyFilters() {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final keyword = _keyword.trim().toLowerCase();

    var jobs = _allJobs.where((job) {
      if (keyword.isNotEmpty) {
        final haystack =
            '${job.contentId} ${job.idea} ${job.status} ${job.format} ${job.publishPlatform}'
                .toLowerCase();
        if (!haystack.contains(keyword)) return false;
      }

      switch (_filter) {
        case QueueFilter.all:
          return true;
        case QueueFilter.today:
          final due = job.plannedDate;
          return due != null &&
              DateTime(due.year, due.month, due.day) == today;
        case QueueFilter.review:
          return job.status == 'READY_FOR_REVIEW';
        case QueueFilter.blocked:
          return job.blocker != null || job.status.endsWith('_FAILED');
        case QueueFilter.published:
          return job.status == 'PUBLISHED' ||
              job.publishStatus == 'PUBLISHED';
      }
    }).toList();

    jobs.sort((a, b) {
      final byStatus = _statusRank(a.status).compareTo(_statusRank(b.status));
      if (byStatus != 0) return byStatus;
      final aDue = a.plannedDate ?? DateTime(2100);
      final bDue = b.plannedDate ?? DateTime(2100);
      final byDue = aDue.compareTo(bDue);
      if (byDue != 0) return byDue;
      return (b.score ?? -1).compareTo(a.score ?? -1);
    });

    setState(() {
      _jobs = jobs;
      _loading = false;
    });
  }

  int _statusRank(String status) {
    const ranks = {
      'READY_FOR_REVIEW': 0,
      'GENERATION_FAILED': 1,
      'ASSET_FAILED': 1,
      'AUDIO_FAILED': 1,
      'RENDER_FAILED': 1,
      'PUBLISH_FAILED': 1,
      'GENERATING': 2,
      'ASSET_QUEUED': 2,
      'ASSET_GENERATING': 2,
      'ASSET_READY': 2,
      'AUDIO_GENERATING': 2,
      'RENDERING': 2,
      'PUBLISHING': 2,
      'SELECTED': 3,
      'SCORED': 4,
      'BACKLOG': 5,
      'NEW': 6,
      'APPROVED': 7,
      'READY_TO_PUBLISH': 8,
      'PUBLISHED': 9,
      'ARCHIVED': 10,
    };
    return ranks[status] ?? 50;
  }

  void _openStickerForge() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const AssetForgePage()),
    );
  }

  Future<void> _openJob(ContentJob job) async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => ContentJobPage(job: job)),
    );
    if (mounted) {
      await _loadJobs();
    }
  }

  int get _reviewCount =>
      _allJobs.where((job) => job.status == 'READY_FOR_REVIEW').length;

  int get _workingCount => _allJobs
      .where((job) => const {
            'GENERATING',
            'ASSET_QUEUED',
            'ASSET_GENERATING',
            'ASSET_READY',
            'AUDIO_GENERATING',
            'RENDERING',
            'PUBLISHING',
          }.contains(job.status))
      .length;

  int get _blockedCount =>
      _allJobs.where((job) => job.blocker != null).length;

  int get _queuedCount => _allJobs
      .where((job) => const {'NEW', 'SCORED', 'SELECTED', 'BACKLOG'}
          .contains(job.status))
      .length;

  int get _activeCount => _allJobs
      .where((job) => !const {'PUBLISHED', 'ARCHIVED'}.contains(job.status))
      .length;

  String _filterLabel(QueueFilter filter) {
    switch (filter) {
      case QueueFilter.all:
        return 'All';
      case QueueFilter.today:
        return 'Today';
      case QueueFilter.review:
        return 'Review';
      case QueueFilter.blocked:
        return 'Blocked';
      case QueueFilter.published:
        return 'Published';
    }
  }

  String _dueLabel(ContentJob job) {
    final due = job.plannedDate;
    if (due == null) return 'No due date';
    return 'Due ${due.day.toString().padLeft(2, '0')}/${due.month.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SoloForge AI'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh),
            onPressed: _loading ? null : _loadJobs,
          ),
          IconButton(
            tooltip: 'Performance',
            icon: const Icon(Icons.insights_outlined),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const AnalyticsPage()),
              );
            },
          ),
          IconButton(
            tooltip: 'Settings',
            icon: const Icon(Icons.settings_outlined),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const SettingsPage()),
              );
            },
          ),
          IconButton(
            tooltip: 'About',
            icon: const Icon(Icons.info_outline),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const AboutPage()),
              );
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadJobs,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 16),
          children: [
            _IdeaComposerCard(
              controller: _ideaController,
              busy: _ideaBusy,
              analysis: _ideaAnalysis,
              error: _ideaError,
              onAnalyze: _analyzeIdea,
              onGenerate: (recommendation) => _createIdeaJob(
                recommendation,
                generateNow: true,
              ),
              onSave: (recommendation) => _createIdeaJob(
                recommendation,
                generateNow: false,
              ),
            ),
            const SizedBox(height: 10),
            HeroBanner(onPressed: _openStickerForge),
            const SizedBox(height: 10),
            _QueueSummary(
              active: _activeCount,
              review: _reviewCount,
              working: _workingCount,
              queued: _queuedCount,
              blocked: _blockedCount,
            ),
            const SizedBox(height: 10),
            TextField(
              onChanged: (value) {
                _keyword = value;
                _applyFilters();
              },
              decoration: InputDecoration(
                hintText: 'Search content jobs...',
                prefixIcon: const Icon(Icons.search, size: 19),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: 38,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: QueueFilter.values.length,
                separatorBuilder: (_, _) => const SizedBox(width: 6),
                itemBuilder: (context, index) {
                  final filter = QueueFilter.values[index];
                  final selected = filter == _filter;
                  return ChoiceChip(
                    selected: selected,
                    label: Text(_filterLabel(filter)),
                    onSelected: (_) {
                      _filter = filter;
                      _applyFilters();
                    },
                  );
                },
              ),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                const Icon(
                  Icons.view_kanban_outlined,
                  size: 18,
                  color: AshColors.indigoMist,
                ),
                const SizedBox(width: 6),
                const Text(
                  'Content Queue',
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    color: AshColors.boneWhite,
                  ),
                ),
                const Spacer(),
                Text(
                  '${_jobs.length} jobs',
                  style: const TextStyle(color: AshColors.smokeSilver),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (_loading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 48),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              _ErrorCard(message: _error!, onRetry: _loadJobs)
            else if (_jobs.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 48),
                child: Center(child: Text('No content jobs in this view.')),
              )
            else
              ..._jobs.map(
                (job) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _ContentJobCard(
                    job: job,
                    dueLabel: _dueLabel(job),
                    onTap: () => _openJob(job),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _IdeaComposerCard extends StatelessWidget {
  const _IdeaComposerCard({
    required this.controller,
    required this.busy,
    required this.analysis,
    required this.error,
    required this.onAnalyze,
    required this.onGenerate,
    required this.onSave,
  });

  final TextEditingController controller;
  final bool busy;
  final IdeaAnalysis? analysis;
  final String? error;
  final VoidCallback onAnalyze;
  final ValueChanged<IdeaRecommendation> onGenerate;
  final ValueChanged<IdeaRecommendation> onSave;

  @override
  Widget build(BuildContext context) {
    final options = analysis?.options ?? const <IdeaRecommendation>[];
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'วันนี้อยากทำคอนเทนต์เรื่องอะไร?',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w900,
                color: AshColors.boneWhite,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'ใส่ไอเดีย แล้ว SoloForge จะแนะนำรูปแบบ Platform และ Hook direction ให้',
              style: TextStyle(color: AshColors.smokeSilver),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              enabled: !busy,
              minLines: 2,
              maxLines: 5,
              decoration: InputDecoration(
                hintText: 'เช่น ทำ AI Character 5 รูป แต่หน้ากลายเป็นคนละคน',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            const SizedBox(height: 10),
            FilledButton.icon(
              onPressed: busy ? null : onAnalyze,
              icon: const Icon(Icons.auto_awesome),
              label: Text(busy ? 'กำลังวิเคราะห์...' : 'Analyze Idea'),
            ),
            if (busy) ...[
              const SizedBox(height: 8),
              const LinearProgressIndicator(),
            ],
            if (error != null) ...[
              const SizedBox(height: 10),
              Text(error!, style: const TextStyle(color: AshColors.mutedRose)),
            ],
            if (analysis != null) ...[
              const SizedBox(height: 14),
              Text(
                'MiniBoss ${analysis!.minibossScore}/100 · ${analysis!.minibossDecision}',
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  color: AshColors.indigoMist,
                ),
              ),
              const SizedBox(height: 10),
              ...options.map(
                (option) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AshColors.blackPlum,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: option.recommended
                            ? AshColors.mutedRose
                            : AshColors.indigoMist.withValues(alpha: 0.35),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                option.title,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w900,
                                  color: AshColors.boneWhite,
                                ),
                              ),
                            ),
                            if (option.recommended)
                              const Chip(label: Text('Recommended')),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(option.reason),
                        const SizedBox(height: 6),
                        Text(
                          '${option.platforms.join(' / ')} · ${option.goal} · Fit ${option.fitScore}',
                          style: const TextStyle(
                            color: AshColors.smokeSilver,
                            fontSize: 12,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Hook: ${option.hookDirection}',
                          style: const TextStyle(
                            color: AshColors.smokeSilver,
                            fontSize: 12,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            Expanded(
                              child: FilledButton(
                                onPressed: busy ? null : () => onGenerate(option),
                                child: const Text('Generate this'),
                              ),
                            ),
                            const SizedBox(width: 8),
                            OutlinedButton(
                              onPressed: busy ? null : () => onSave(option),
                              child: const Text('Save idea'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
class _QueueSummary extends StatelessWidget {
  const _QueueSummary({
    required this.active,
    required this.review,
    required this.working,
    required this.queued,
    required this.blocked,
  });

  final int active;
  final int review;
  final int working;
  final int queued;
  final int blocked;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '$active Active Jobs',
              style: const TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _CountPill(label: 'Review', value: review),
                _CountPill(label: 'Working', value: working),
                _CountPill(label: 'Queued', value: queued),
                _CountPill(label: 'Blocked', value: blocked),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _CountPill extends StatelessWidget {
  const _CountPill({required this.label, required this.value});
  final String label;
  final int value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: AshColors.blackPlum,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: AshColors.indigoMist.withValues(alpha: 0.35),
        ),
      ),
      child: Text('$label $value'),
    );
  }
}

class _ContentJobCard extends StatelessWidget {
  const _ContentJobCard({
    required this.job,
    required this.dueLabel,
    required this.onTap,
  });

  final ContentJob job;
  final String dueLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                    decoration: BoxDecoration(
                      color: AshColors.blackPlum,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      job.contentId,
                      style: const TextStyle(fontWeight: FontWeight.w900),
                    ),
                  ),
                  const Spacer(),
                  _StatusBadge(status: job.status),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                job.idea,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  color: AshColors.boneWhite,
                ),
              ),
              const SizedBox(height: 9),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  Text('★ ${job.score?.toStringAsFixed(0) ?? '-'}'),
                  Text(job.publishPlatform),
                  Text(job.format),
                  Text(dueLabel),
                ],
              ),
              if (job.blocker != null) ...[
                const SizedBox(height: 9),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.warning_amber_rounded,
                      size: 16,
                      color: AshColors.mutedRose,
                    ),
                    const SizedBox(width: 5),
                    Expanded(
                      child: Text(
                        job.blocker!,
                        style: const TextStyle(color: AshColors.mutedRose),
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});
  final String status;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 155),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(9),
        border: Border.all(
          color: AshColors.indigoMist.withValues(alpha: 0.5),
        ),
      ),
      child: Text(
        status.replaceAll('_', ' '),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800),
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  const _ErrorCard({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            const Icon(Icons.lock_outline),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: onRetry,
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
