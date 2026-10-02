import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import '../models/content_job.dart';
import '../services/content_job_service.dart';
import '../widgets/content/publishing_dialogs.dart';

class ContentQualityReview {
  const ContentQualityReview({
    required this.status,
    required this.reason,
    required this.matchedAnchors,
    required this.requiredAnchors,
    required this.available,
  });

  final String status;
  final String reason;
  final List<String> matchedAnchors;
  final List<String> requiredAnchors;
  final bool available;

  bool get blocksApproval =>
      available && (status == 'FAIL' || status == 'STALE');

  static ContentQualityReview fromJob(ContentJob job) {
    final raw = job.contentPackage['semantic_fidelity'];
    if (raw is! Map) {
      return const ContentQualityReview(
        status: 'NOT_AVAILABLE',
        reason: 'Semantic fidelity metadata is not available for this job.',
        matchedAnchors: [],
        requiredAnchors: [],
        available: false,
      );
    }

    List<String> strings(dynamic value) {
      if (value is! List) return const [];
      return value
          .map((item) => item.toString().trim())
          .where((item) => item.isNotEmpty)
          .toList(growable: false);
    }

    final status = raw['status']?.toString().trim().toUpperCase();
    final generatedAt = job.generatedAt;
    final updatedAt = job.updatedAt;
    final stale = generatedAt != null &&
        updatedAt != null &&
        updatedAt.isAfter(generatedAt.add(const Duration(seconds: 2)));

    return ContentQualityReview(
      status: stale
          ? 'STALE'
          : (status == null || status.isEmpty ? 'NOT_AVAILABLE' : status),
      reason: stale
          ? 'Draft changed after AI generation. Regenerate before approval so semantic fidelity can be checked again.'
          : (raw['reason']?.toString().trim().isNotEmpty == true
              ? raw['reason'].toString().trim()
              : 'No semantic fidelity reason was recorded.'),
      matchedAnchors: strings(raw['matched_anchors']),
      requiredAnchors: strings(raw['required_anchors']),
      available: status != null && status.isNotEmpty,
    );
  }
}

class ContentJobPage extends StatefulWidget {
  const ContentJobPage({super.key, required this.job});

  final ContentJob job;

  @override
  State<ContentJobPage> createState() => _ContentJobPageState();
}

class _ContentJobPageState extends State<ContentJobPage> {
  final ContentJobService _service = ContentJobService();

  late ContentJob _job;
  late final TextEditingController _hook;
  late final TextEditingController _script;
  late final TextEditingController _caption;
  late final TextEditingController _cta;
  late final TextEditingController _visualPrompt;
  late final TextEditingController _motionPrompt;

  bool _busy = false;
  bool _editing = false;
  String? _error;
  ContentFeedback? _feedback;

  @override
  void initState() {
    super.initState();
    _job = widget.job;
    _hook = TextEditingController(text: _job.hook ?? '');
    _script = TextEditingController(text: _job.script ?? '');
    _caption = TextEditingController(text: _job.caption ?? '');
    _cta = TextEditingController(text: _job.cta ?? '');
    _visualPrompt = TextEditingController(text: _job.visualPrompt ?? '');
    _motionPrompt = TextEditingController(text: _job.motionPrompt ?? '');
    _loadFeedback();
  }

  Future<void> _loadFeedback() async {
    try {
      final feedback = await _service.getPerformanceFeedback(_job.id);
      if (!mounted) return;
      setState(() => _feedback = feedback);
    } catch (_) {
      // Feedback is advisory and must never block the content workflow.
    }
  }

  @override
  void dispose() {
    _hook.dispose();
    _script.dispose();
    _caption.dispose();
    _cta.dispose();
    _visualPrompt.dispose();
    _motionPrompt.dispose();
    super.dispose();
  }

  void _syncControllers(ContentJob job) {
    _hook.text = job.hook ?? '';
    _script.text = job.script ?? '';
    _caption.text = job.caption ?? '';
    _cta.text = job.cta ?? '';
    _visualPrompt.text = job.visualPrompt ?? '';
    _motionPrompt.text = job.motionPrompt ?? '';
  }

  Future<void> _run(Future<ContentJob> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final updated = await action();
      if (!mounted) return;
      setState(() {
        _job = updated;
        _editing = false;
      });
      _syncControllers(updated);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _save() => _run(
        () => _service.updateDraft(
          _job.id,
          hook: _hook.text.trim(),
          script: _script.text.trim(),
          caption: _caption.text.trim(),
          cta: _cta.text.trim(),
          visualPrompt: _visualPrompt.text.trim(),
          motionPrompt: _motionPrompt.text.trim(),
        ),
      );

  Future<void> _approve() => _run(() => _service.approve(_job.id));

  Future<void> _publishNow() async {
    try {
      final plan = await choosePublishingPlan(
        context,
        service: _service,
        job: _job,
        schedule: false,
      );
      if (plan == null || !mounted) return;

      final confirmed = await showDialog<bool>(
            context: context,
            builder: (dialogContext) => AlertDialog(
              title: const Text('Publish now?'),
              content: const Text(
                'SoloForge will send this content to Publora and queue a real post shortly.',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext, false),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(dialogContext, true),
                  child: const Text('Publish Now'),
                ),
              ],
            ),
          ) ??
          false;

      if (!confirmed || !mounted) return;
      await _run(
        () => _service.publishNow(
          _job.id,
          platformIds: plan.platformIds,
        ),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _schedulePublish() async {
    try {
      final plan = await choosePublishingPlan(
        context,
        service: _service,
        job: _job,
        schedule: true,
      );
      if (plan == null || plan.scheduledTime == null || !mounted) return;
      await _run(
        () => _service.schedule(
          _job.id,
          platformIds: plan.platformIds,
          scheduledTime: plan.scheduledTime!,
        ),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _regenerate() async {
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Regenerate draft?'),
            content: const Text(
              'Generated text and prompts will be cleared. The content brief and queue metadata will be kept.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Regenerate'),
              ),
            ],
          ),
        ) ??
        false;
    if (!confirmed || !mounted) return;
    await _run(() => _service.regenerate(_job.id));
  }

  bool get _canEdit =>
      _job.status == 'READY_FOR_REVIEW' || _job.status == 'BACKLOG';

  ContentQualityReview get _qualityReview =>
      ContentQualityReview.fromJob(_job);

  bool get _canApprove =>
      _job.status == 'READY_FOR_REVIEW' && !_qualityReview.blocksApproval;
  bool get _canPublish => _job.status == 'READY_TO_PUBLISH';

  bool get _canRegenerate => const {
        'BACKLOG',
        'READY_FOR_REVIEW',
        'GENERATION_FAILED',
        'SELECTED',
      }.contains(_job.status);

  @override
  Widget build(BuildContext context) {
    return PopScope(
      onPopInvokedWithResult: (_, _) {},
      child: Scaffold(
        appBar: AppBar(
          title: Text(_job.contentId),
          actions: [
            if (_canEdit)
              IconButton(
                tooltip: _editing ? 'Cancel edit' : 'Edit draft',
                onPressed: _busy
                    ? null
                    : () => setState(() => _editing = !_editing),
                icon: Icon(_editing ? Icons.close : Icons.edit_outlined),
              ),
          ],
        ),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(_job.idea, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _Chip(label: _job.status),
                _Chip(
                  label: 'MiniBoss ${_job.score?.toStringAsFixed(0) ?? '-'}',
                ),
                _Chip(label: _job.publishPlatform),
                _Chip(label: _job.format),
                _Chip(label: _job.priority),
                if (_job.pipelineRoute != '-')
                  _Chip(label: 'Route ${_job.pipelineRoute}'),
                if (_job.assetStatus != '-')
                  _Chip(label: 'Asset ${_job.assetStatus}'),
                if (_job.publishStatus.isNotEmpty)
                  _Chip(label: 'Publish ${_job.publishStatus}'),
              ],
            ),
            if (_job.blocker != null) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.warning_amber_rounded),
                      const SizedBox(width: 8),
                      Expanded(child: Text(_job.blocker!)),
                    ],
                  ),
                ),
              ),
            ],
            if (_error != null) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                    _error!,
                    style: const TextStyle(color: AshColors.mutedRose),
                  ),
                ),
              ),
            ],
            if (_busy) ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(),
            ],
            const SizedBox(height: 16),
            _ContentQualityReviewCard(
              idea: _job.idea,
              hook: _hook.text,
              caption: _caption.text,
              provider: _job.generatorProvider,
              model: _job.generatorModel,
              review: _qualityReview,
            ),
            const SizedBox(height: 4),
            _DraftField(
              title: 'Hook',
              controller: _hook,
              editing: _editing,
              maxLines: 4,
            ),
            _DraftField(
              title: 'Script',
              controller: _script,
              editing: _editing,
              maxLines: 12,
            ),
            _DraftField(
              title: 'Caption',
              controller: _caption,
              editing: _editing,
              maxLines: 8,
            ),
            _DraftField(
              title: 'CTA',
              controller: _cta,
              editing: _editing,
              maxLines: 4,
            ),
            _DraftField(
              title: 'Visual Prompt',
              controller: _visualPrompt,
              editing: _editing,
              maxLines: 8,
            ),
            _DraftField(
              title: 'Motion Prompt',
              controller: _motionPrompt,
              editing: _editing,
              maxLines: 8,
            ),
            _ReadOnlySection(title: 'Goal', value: _job.goal),
            _ReadOnlySection(
              title: 'Pipeline Route',
              value: _job.pipelineRoute,
            ),
            _ReadOnlySection(
              title: 'Asset Status',
              value: _job.assetStatus,
            ),
            if (_job.publoraPostId != null)
              _ReadOnlySection(
                title: 'Publora Post',
                value: _job.publoraPostId,
              ),
            if (_job.scheduledTime != null)
              _ReadOnlySection(
                title: 'Scheduled',
                value: _job.scheduledTime!.toLocal().toString(),
              ),
            if (_job.publishedAt != null)
              _ReadOnlySection(
                title: 'Published',
                value: _job.publishedAt!.toLocal().toString(),
              ),
            _ReadOnlySection(
              title: 'MiniBoss Reason',
              value: _job.scoreReason,
            ),
            if (_feedback != null)
              Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Performance Feedback',
                        style: TextStyle(
                          color: AshColors.mutedRose,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _feedback!.state == 'READY'
                            ? '${_feedback!.automationAction.replaceAll('_', ' ')} · advisory score ${_feedback!.scoreAdjustment >= 0 ? '+' : ''}${_feedback!.scoreAdjustment}'
                            : 'Collect more data · ${_feedback!.sampleSize}/${_feedback!.minimumSampleSize} comparable series',
                      ),
                      if (_feedback!.reasons.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          _feedback!.reasons.join(' · '),
                          style: const TextStyle(color: AshColors.smokeSilver),
                        ),
                      ],
                      const SizedBox(height: 6),
                      const Text(
                        'Advisory only — this does not auto-publish or override the deterministic MiniBoss decision.',
                        style: TextStyle(
                          color: AshColors.smokeSilver,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 6),
            if (_editing)
              FilledButton.icon(
                onPressed: _busy ? null : _save,
                icon: const Icon(Icons.save_outlined),
                label: const Text('Save Draft'),
              ),
            if (!_editing) ...[
              if (_job.status == 'READY_FOR_REVIEW' &&
                  _qualityReview.blocksApproval) ...[
                Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.block_outlined,
                          color: AshColors.mutedRose,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _qualityReview.status == 'STALE'
                                ? 'Approval blocked: draft changed after AI generation. Regenerate to run semantic QA again.'
                                : 'Approval blocked: generated content failed semantic fidelity QA.',
                            style: const TextStyle(
                              color: AshColors.mutedRose,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              if (_canApprove)
                FilledButton.icon(
                  onPressed: _busy ? null : _approve,
                  icon: const Icon(Icons.check_circle_outline),
                  label: const Text('Approve'),
                ),
              if (_job.status == 'READY_FOR_REVIEW') const SizedBox(height: 8),
              if (_canRegenerate)
                OutlinedButton.icon(
                  onPressed: _busy ? null : _regenerate,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Regenerate'),
                ),
              if (_canPublish) ...[
                const SizedBox(height: 14),
                FilledButton.icon(
                  onPressed: _busy ? null : _publishNow,
                  icon: const Icon(Icons.send_outlined),
                  label: const Text('Publish Now'),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: _busy ? null : _schedulePublish,
                  icon: const Icon(Icons.schedule_outlined),
                  label: const Text('Schedule'),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}

class _ContentQualityReviewCard extends StatelessWidget {
  const _ContentQualityReviewCard({
    required this.idea,
    required this.hook,
    required this.caption,
    required this.provider,
    required this.model,
    required this.review,
  });

  final String idea;
  final String hook;
  final String caption;
  final String? provider;
  final String? model;
  final ContentQualityReview review;

  String get _statusLabel {
    if (!review.available) return 'Not available';
    if (review.status == 'PASS') return 'PASS';
    if (review.status == 'FAIL') return 'FAIL';
    if (review.status == 'STALE') return 'Needs recheck';
    return review.status;
  }

  @override
  Widget build(BuildContext context) {
    final generated = [
      if (hook.trim().isNotEmpty) 'Hook: ${hook.trim()}',
      if (caption.trim().isNotEmpty) 'Caption: ${caption.trim()}',
    ].join('\n\n');

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Content Quality Review',
              style: TextStyle(
                color: AshColors.mutedRose,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Original Idea',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 5),
            Text(idea.trim().isEmpty ? '—' : idea.trim()),
            const SizedBox(height: 12),
            const Text(
              'Generated Content',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 5),
            Text(generated.isEmpty ? '—' : generated),
            const SizedBox(height: 12),
            Row(
              children: [
                const Text(
                  'Semantic Fidelity',
                  style: TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(width: 8),
                _Chip(label: _statusLabel),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              review.reason,
              style: const TextStyle(color: AshColors.smokeSilver),
            ),
            if (review.requiredAnchors.isNotEmpty) ...[
              const SizedBox(height: 7),
              Text(
                'Required: ${review.requiredAnchors.join(', ')}',
                style: const TextStyle(
                  color: AshColors.smokeSilver,
                  fontSize: 12,
                ),
              ),
            ],
            if (review.matchedAnchors.isNotEmpty) ...[
              const SizedBox(height: 3),
              Text(
                'Matched: ${review.matchedAnchors.join(', ')}',
                style: const TextStyle(
                  color: AshColors.smokeSilver,
                  fontSize: 12,
                ),
              ),
            ],
            if ((provider?.trim().isNotEmpty ?? false) ||
                (model?.trim().isNotEmpty ?? false)) ...[
              const SizedBox(height: 7),
              Text(
                'Generated by ${provider?.trim().isNotEmpty == true ? provider!.trim() : 'unknown'}'
                '${model?.trim().isNotEmpty == true ? ' · ${model!.trim()}' : ''}',
                style: const TextStyle(
                  color: AshColors.smokeSilver,
                  fontSize: 12,
                ),
              ),
            ],
            if (!review.available) ...[
              const SizedBox(height: 7),
              const Text(
                'Legacy job: review the draft manually before approval.',
                style: TextStyle(
                  color: AshColors.smokeSilver,
                  fontSize: 12,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DraftField extends StatelessWidget {
  const _DraftField({
    required this.title,
    required this.controller,
    required this.editing,
    required this.maxLines,
  });

  final String title;
  final TextEditingController controller;
  final bool editing;
  final int maxLines;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                color: AshColors.mutedRose,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            if (editing)
              TextField(
                controller: controller,
                minLines: 1,
                maxLines: maxLines,
              )
            else
              Text(
                controller.text.trim().isEmpty ? '—' : controller.text,
              ),
          ],
        ),
      ),
    );
  }
}

class _ReadOnlySection extends StatelessWidget {
  const _ReadOnlySection({required this.title, required this.value});

  final String title;
  final String? value;

  @override
  Widget build(BuildContext context) {
    final text = value?.trim();
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                color: AshColors.mutedRose,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(text == null || text.isEmpty ? '—' : text),
          ],
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text(label),
      side: BorderSide(color: AshColors.indigoMist.withValues(alpha: 0.5)),
    );
  }
}
