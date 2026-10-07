import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import '../models/content_job.dart';
import '../services/content_job_service.dart';
import '../services/pollinations_session_service.dart';
import '../widgets/home/hero_banner.dart';
import 'about_page.dart';
import 'analytics_page.dart';
import 'asset_forge_page.dart';
import 'content_job_page.dart';
import 'settings_page.dart';
import 'prawtwan_chat_page.dart';
import '../services/prawtwan_oauth_return.dart';

enum QueueFilter { all, actionRequired, processing, completed, backlog }

class JobQueuePresentation {
  static bool matchesSearch(ContentJob job, String query) {
    final terms = query
        .trim()
        .toLowerCase()
        .split(RegExp(r'\s+'))
        .where((term) => term.isNotEmpty)
        .toList(growable: false);
    if (terms.isEmpty) return true;

    final haystack = [
      job.contentId,
      job.idea,
      job.status,
      statusLabel(job.status),
      actionLabel(job),
      job.format,
      job.publishPlatform,
      groupFor(job).name,
    ].join(' ').toLowerCase();

    return terms.every(haystack.contains);
  }

  static const _processingStatuses = {
    'GENERATING',
    'APPROVED',
    'ASSET_QUEUED',
    'ASSET_GENERATING',
    'ASSET_READY',
    'AUDIO_GENERATING',
    'AUDIO_READY',
    'FINAL_RENDERING',
    'RENDERING',
    'PUBLISHING',
  };

  static const _backlogStatuses = {
    'NEW',
    'SCORED',
    'SELECTED',
    'BACKLOG',
    'ARCHIVED',
  };

  static bool isFailure(ContentJob job) =>
      job.status.endsWith('_FAILED') ||
      (job.blocker != null && job.status != 'BACKLOG');

  static QueueFilter groupFor(ContentJob job) {
    if (job.status == 'READY_FOR_REVIEW' ||
        job.status == 'READY_TO_PUBLISH' ||
        isFailure(job)) {
      return QueueFilter.actionRequired;
    }
    if (_processingStatuses.contains(job.status)) {
      return QueueFilter.processing;
    }
    if (job.status == 'PUBLISHED' || job.publishStatus == 'PUBLISHED') {
      return QueueFilter.completed;
    }
    if (_backlogStatuses.contains(job.status)) {
      return QueueFilter.backlog;
    }
    return QueueFilter.backlog;
  }

  static String statusLabel(String status) {
    const labels = {
      'NEW': 'New',
      'SCORING': 'Scoring',
      'SCORED': 'Scored',
      'SELECTED': 'Queued',
      'BACKLOG': 'Backlog',
      'ARCHIVED': 'Archived',
      'GENERATING': 'Generating',
      'READY_FOR_REVIEW': 'Ready for Review',
      'APPROVED': 'Approved',
      'ASSET_QUEUED': 'Asset Queued',
      'ASSET_GENERATING': 'Generating Asset',
      'ASSET_READY': 'Asset Ready',
      'ASSET_FAILED': 'Asset Failed',
      'AUDIO_GENERATING': 'Generating Audio',
      'AUDIO_READY': 'Audio Ready',
      'AUDIO_FAILED': 'Audio Failed',
      'FINAL_RENDERING': 'Final Rendering',
      'RENDERING': 'Rendering',
      'RENDER_FAILED': 'Render Failed',
      'READY_TO_PUBLISH': 'Ready to Publish',
      'PUBLISHING': 'Publishing',
      'PUBLISHED': 'Published',
      'GENERATION_FAILED': 'Generation Failed',
      'PUBLISH_FAILED': 'Publish Failed',
    };
    return labels[status] ?? status.replaceAll('_', ' ');
  }

  static String actionLabel(ContentJob job) {
    if (job.status == 'READY_FOR_REVIEW') return 'Review now';
    if (job.status == 'READY_TO_PUBLISH') return 'Publish now';
    if (isFailure(job)) return 'Needs attention';
    if (groupFor(job) == QueueFilter.processing) return 'Processing';
    if (groupFor(job) == QueueFilter.completed) return 'Completed';
    return 'Saved for later';
  }

  static int statusRank(ContentJob job) {
    switch (groupFor(job)) {
      case QueueFilter.actionRequired:
        return job.status == 'READY_FOR_REVIEW' ||
                job.status == 'READY_TO_PUBLISH'
            ? 0
            : 1;
      case QueueFilter.processing:
        return 2;
      case QueueFilter.backlog:
        return job.status == 'ARCHIVED' ? 4 : 3;
      case QueueFilter.completed:
        return 5;
      case QueueFilter.all:
        return 6;
    }
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final ContentJobService _contentJobService = ContentJobService();
  final PollinationsSessionService _pollinationsSession =
      PollinationsSessionService();
  final TextEditingController _ideaController = TextEditingController();
  final TextEditingController _searchController = TextEditingController();

  List<ContentJob> _allJobs = const [];
  List<ContentJob> _jobs = const [];
  QueueFilter _filter = QueueFilter.all;
  String _keyword = '';
  bool _loading = true;
  bool _ideaBusy = false;
  bool _pollinationsLoading = true;
  bool _pollinationsConnected = false;
  bool _pollinationsConnecting = false;
  IdeaAnalysis? _ideaAnalysis;
  String? _ideaError;
  String? _error;
  String? _pollinationsError;

  @override
  void initState() {
    super.initState();
    final restored = takePrawtwanReturn();
    if (restored == null) {
      _loadPollinationsConnection();
    } else {
      WidgetsBinding.instance.addPostFrameCallback((_) async {
        if (!mounted) return;
        await Navigator.push(context, MaterialPageRoute(
          builder: (_) => PrawtwanChatPage(restored: restored),
        ));
        if (mounted) _loadPollinationsConnection();
      });
    }
    _loadJobs();
  }

  @override
  void dispose() {
    _pollinationsSession.dispose();
    _ideaController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadPollinationsConnection() async {
    if (mounted) {
      setState(() {
        _pollinationsLoading = true;
        _pollinationsError = null;
      });
    }

    try {
      if (!kIsWeb) {
        await _pollinationsSession.startListening(
          onCallback: (uri) async {
            // The foreground page owns one-time handoff exchange.
            if (!mounted || ModalRoute.of(context)?.isCurrent != true) return;
            if (!_pollinationsSession.isPollinationsCallback(uri)) return;
            final state = await _pollinationsSession.handleCallback(uri);
            if (!mounted) return;
            setState(() {
              _pollinationsConnected = state.connected;
              _pollinationsLoading = false;
              _pollinationsConnecting = false;
              _pollinationsError = null;
            });
          },
        );
      }

      final state = kIsWeb
          ? await _pollinationsSession.handleWebCallbackIfPresent()
          : await _pollinationsSession.status();
      if (!mounted) return;
      setState(() {
        _pollinationsConnected = state.connected;
        _pollinationsLoading = false;
        _pollinationsConnecting = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _pollinationsConnected = false;
        _pollinationsLoading = false;
        _pollinationsConnecting = false;
        _pollinationsError = error.toString();
      });
    }
  }

  Future<void> _connectPollinations() async {
    if (_pollinationsConnecting) return;
    setState(() {
      _pollinationsConnecting = true;
      _pollinationsError = null;
    });

    try {
      await _pollinationsSession.connect();
      if (!kIsWeb && mounted) {
        setState(() => _pollinationsConnecting = false);
      }
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _pollinationsConnecting = false;
        _pollinationsError = error.toString();
      });
    }
  }

  Future<void> _disconnectPollinations() async {
    if (_pollinationsConnecting) return;
    setState(() {
      _pollinationsConnecting = true;
      _pollinationsError = null;
    });
    try {
      await _pollinationsSession.disconnect();
      if (!mounted) return;
      setState(() {
        _pollinationsConnected = false;
        _pollinationsConnecting = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _pollinationsConnecting = false;
        _pollinationsError = error.toString();
      });
    }
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
    final keyword = _keyword.trim().toLowerCase();

    var jobs = _allJobs.where((job) {
      if (!JobQueuePresentation.matchesSearch(job, keyword)) {
        return false;
      }

      switch (_filter) {
        case QueueFilter.all:
          return true;
        case QueueFilter.actionRequired:
        case QueueFilter.processing:
        case QueueFilter.completed:
        case QueueFilter.backlog:
          return JobQueuePresentation.groupFor(job) == _filter;
      }
    }).toList();

    jobs.sort((a, b) {
      final byStatus = JobQueuePresentation.statusRank(a)
          .compareTo(JobQueuePresentation.statusRank(b));
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

  int get _actionRequiredCount => _allJobs
      .where((job) =>
          JobQueuePresentation.groupFor(job) == QueueFilter.actionRequired)
      .length;

  int get _processingCount => _allJobs
      .where((job) =>
          JobQueuePresentation.groupFor(job) == QueueFilter.processing)
      .length;

  int get _backlogCount => _allJobs
      .where((job) =>
          JobQueuePresentation.groupFor(job) == QueueFilter.backlog)
      .length;

  int get _completedCount => _allJobs
      .where((job) =>
          JobQueuePresentation.groupFor(job) == QueueFilter.completed)
      .length;

  int get _activeCount => _allJobs
      .where((job) => !const {'PUBLISHED', 'ARCHIVED'}.contains(job.status))
      .length;

  int _filterCount(QueueFilter filter) {
    if (filter == QueueFilter.all) return _allJobs.length;
    return _allJobs
        .where((job) => JobQueuePresentation.groupFor(job) == filter)
        .length;
  }

  String _filterLabel(QueueFilter filter) {
    switch (filter) {
      case QueueFilter.all:
        return 'All';
      case QueueFilter.actionRequired:
        return 'Action Required';
      case QueueFilter.processing:
        return 'Processing';
      case QueueFilter.completed:
        return 'Completed';
      case QueueFilter.backlog:
        return 'Backlog';
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
            Card(
              margin: EdgeInsets.zero,
              child: ListTile(
                leading: const Icon(Icons.auto_stories_outlined),
                title: const Text('Prawtwan · พี่พราว'),
                subtitle: const Text('ผู้ช่วยงานเขียนนิยาย · Fiction editor'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const PrawtwanChatPage()),
                ),
              ),
            ),
            const SizedBox(height: 10),
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
            _PollinationsConnectionCard(
              loading: _pollinationsLoading,
              connected: _pollinationsConnected,
              connecting: _pollinationsConnecting,
              error: _pollinationsError,
              onConnect: _connectPollinations,
              onDisconnect: _disconnectPollinations,
              onRefresh: _loadPollinationsConnection,
            ),
            const SizedBox(height: 10),
            HeroBanner(onPressed: _openStickerForge),
            const SizedBox(height: 10),
            _QueueSummary(
              active: _activeCount,
              actionRequired: _actionRequiredCount,
              processing: _processingCount,
              backlog: _backlogCount,
              completed: _completedCount,
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _searchController,
              onChanged: (value) {
                _keyword = value;
                _applyFilters();
              },
              decoration: InputDecoration(
                hintText: 'Search idea, status, platform, format...',
                prefixIcon: const Icon(Icons.search, size: 19),
                suffixIcon: _keyword.trim().isEmpty
                    ? null
                    : IconButton(
                        tooltip: 'Clear search',
                        icon: const Icon(Icons.close, size: 18),
                        onPressed: () {
                          _searchController.clear();
                          _keyword = '';
                          _applyFilters();
                        },
                      ),
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
                    label: Text(
                      '${_filterLabel(filter)} (${_filterCount(filter)})',
                    ),
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
                  _jobs.length == _allJobs.length
                      ? '${_jobs.length} jobs'
                      : '${_jobs.length} of ${_allJobs.length}',
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
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 48),
                child: Center(
                  child: Column(
                    children: [
                      const Text('No content jobs match this view.'),
                      if (_keyword.trim().isNotEmpty || _filter != QueueFilter.all) ...[
                        const SizedBox(height: 10),
                        OutlinedButton.icon(
                          onPressed: () {
                            _searchController.clear();
                            _keyword = '';
                            _filter = QueueFilter.all;
                            _applyFilters();
                          },
                          icon: const Icon(Icons.filter_alt_off_outlined),
                          label: const Text('Clear search & filters'),
                        ),
                      ],
                    ],
                  ),
                ),
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

class _PollinationsConnectionCard extends StatelessWidget {
  const _PollinationsConnectionCard({
    required this.loading,
    required this.connected,
    required this.connecting,
    required this.error,
    required this.onConnect,
    required this.onDisconnect,
    required this.onRefresh,
  });

  final bool loading;
  final bool connected;
  final bool connecting;
  final String? error;
  final VoidCallback onConnect;
  final VoidCallback onDisconnect;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final statusColor = connected ? Colors.greenAccent : AshColors.smokeSilver;
    final statusLabel = connected ? 'Connected' : 'Not connected';

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.hub_outlined,
                  color: AshColors.indigoMist,
                ),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'Pollinations',
                    style: TextStyle(
                      fontWeight: FontWeight.w900,
                      color: AshColors.boneWhite,
                    ),
                  ),
                ),
                if (loading)
                  const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                else ...[
                  Icon(Icons.circle, size: 10, color: statusColor),
                  const SizedBox(width: 6),
                  Text(
                    statusLabel,
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      color: statusColor,
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 8),
            Text(
              connected
                  ? 'AI generation powered by Pollinations.ai. This device is authorized.'
                  : 'Connect a Pollinations account to use AI generation with that user\'s Pollen.',
              style: const TextStyle(color: AshColors.smokeSilver),
            ),
            if (error != null && error!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                error!,
                style: const TextStyle(color: AshColors.mutedRose),
              ),
            ],
            const SizedBox(height: 10),
            Row(
              children: [
                if (!connected)
                  FilledButton.icon(
                    onPressed: loading || connecting ? null : onConnect,
                    icon: const Icon(Icons.link),
                    label: Text(
                      connecting ? 'Connecting...' : 'Connect Pollinations',
                    ),
                  )
                else
                  OutlinedButton.icon(
                    onPressed: connecting ? null : onDisconnect,
                    icon: const Icon(Icons.link_off),
                    label: const Text('Disconnect'),
                  ),
                const SizedBox(width: 8),
                IconButton(
                  tooltip: 'Refresh Pollinations status',
                  onPressed: loading || connecting ? null : onRefresh,
                  icon: const Icon(Icons.refresh),
                ),
              ],
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

  String _priorityLabel(String decision) {
    switch (decision) {
      case 'SELECTED':
        return 'พร้อมทำ';
      case 'BACKLOG':
        return 'คิวสำรอง';
      case 'ARCHIVED':
        return 'ไอเดียสำรอง';
      default:
        return decision;
    }
  }

  @override
  Widget build(BuildContext context) {
    final options = analysis?.options ?? const <IdeaRecommendation>[];
    final recommended = options.isEmpty
        ? null
        : options.firstWhere(
            (item) => item.recommended,
            orElse: () => options.first,
          );
    final alternatives = recommended == null
        ? const <IdeaRecommendation>[]
        : options.where((item) => item.id != recommended.id).toList();

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
                'MiniBoss ${analysis!.minibossScore}/100 · ${_priorityLabel(analysis!.minibossDecision)}',
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  color: AshColors.indigoMist,
                ),
              ),
              if (analysis!.minibossDecision == 'ARCHIVED') ...[
                const SizedBox(height: 4),
                const Text(
                  'คะแนนนี้ใช้จัดลำดับไอเดียเท่านั้น คุณยังเลือกสร้างคอนเทนต์นี้ได้',
                  style: TextStyle(
                    color: AshColors.smokeSilver,
                    fontSize: 12,
                  ),
                ),
              ],
              const SizedBox(height: 10),
              if (recommended != null)
                _IdeaRecommendationCard(
                  option: recommended,
                  busy: busy,
                  onGenerate: onGenerate,
                  onSave: onSave,
                ),
              if (alternatives.isNotEmpty) ...[
                const SizedBox(height: 4),
                ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  childrenPadding: EdgeInsets.zero,
                  title: Text(
                    'ดูตัวเลือกอื่น (${alternatives.length})',
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      color: AshColors.smokeSilver,
                    ),
                  ),
                  children: [
                    ...alternatives.map(
                      (option) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: _IdeaRecommendationCard(
                          option: option,
                          busy: busy,
                          onGenerate: onGenerate,
                          onSave: onSave,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}

class _IdeaRecommendationCard extends StatelessWidget {
  const _IdeaRecommendationCard({
    required this.option,
    required this.busy,
    required this.onGenerate,
    required this.onSave,
  });

  final IdeaRecommendation option;
  final bool busy;
  final ValueChanged<IdeaRecommendation> onGenerate;
  final ValueChanged<IdeaRecommendation> onSave;

  @override
  Widget build(BuildContext context) {
    return Container(
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
    );
  }
}

class _QueueSummary extends StatelessWidget {
  const _QueueSummary({
    required this.active,
    required this.actionRequired,
    required this.processing,
    required this.backlog,
    required this.completed,
  });

  final int active;
  final int actionRequired;
  final int processing;
  final int backlog;
  final int completed;

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
                _CountPill(label: 'Action', value: actionRequired),
                _CountPill(label: 'Processing', value: processing),
                _CountPill(label: 'Backlog', value: backlog),
                _CountPill(label: 'Completed', value: completed),
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
                  Expanded(
                    child: Text(
                      job.idea,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        color: AshColors.boneWhite,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  _StatusBadge(status: job.status),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Job #${job.contentId} · ${job.publishPlatform} · ${job.format}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: AshColors.smokeSilver,
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 9),
              Row(
                children: [
                  Expanded(
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: [
                        Text('★ ${job.score?.toStringAsFixed(0) ?? '-'}'),
                        Text(dueLabel),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    JobQueuePresentation.actionLabel(job),
                    style: const TextStyle(
                      color: AshColors.indigoMist,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(width: 2),
                  const Icon(
                    Icons.chevron_right,
                    size: 18,
                    color: AshColors.indigoMist,
                  ),
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
        JobQueuePresentation.statusLabel(status),
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
