import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import '../models/content_job.dart';

class ContentJobPage extends StatelessWidget {
  const ContentJobPage({super.key, required this.job});

  final ContentJob job;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(job.contentId)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(job.idea, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _Chip(label: job.status),
              _Chip(label: 'MiniBoss ${job.score?.toStringAsFixed(0) ?? '-'}'),
              _Chip(label: job.publishPlatform),
              _Chip(label: job.format),
              _Chip(label: job.priority),
            ],
          ),
          if (job.blocker != null) ...[
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.warning_amber_rounded),
                    const SizedBox(width: 8),
                    Expanded(child: Text(job.blocker!)),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 16),
          _Section(title: 'Hook', value: job.hook),
          _Section(title: 'Script', value: job.script),
          _Section(title: 'Caption', value: job.caption),
          _Section(title: 'CTA', value: job.cta),
          _Section(title: 'Visual Prompt', value: job.visualPrompt),
          _Section(title: 'Motion Prompt', value: job.motionPrompt),
          _Section(title: 'Goal', value: job.goal),
          _Section(title: 'MiniBoss Reason', value: job.scoreReason),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.value});

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
                color: AshColors.wineRose,
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
