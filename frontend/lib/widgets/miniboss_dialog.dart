import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../ai/content_engine.dart';
import '../ai/platforms.dart';
import '../engine/miniboss_engine.dart';
import '../models/generated_content.dart';
import '../models/product.dart';

class MiniBossDialog extends StatefulWidget {
  final Product product;

  const MiniBossDialog({
    super.key,
    required this.product,
  });

  @override
  State<MiniBossDialog> createState() => _MiniBossDialogState();
}

class _MiniBossDialogState extends State<MiniBossDialog> {
  bool _loading = false;
  GeneratedContent? _generatedContent;

  Future<void> _generateContent() async {
    setState(() {
      _loading = true;
    });

    final result = await ContentEngine.generateContent(
      product: widget.product,
      platform: PlatformType.tiktok,
    );

    if (!mounted) return;

    setState(() {
      _generatedContent = result;
      _loading = false;
    });
  }

  Future<void> _copyText(String text, String message) async {
    await Clipboard.setData(ClipboardData(text: text));

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  String _buildPostText(GeneratedContent content) {
    return [
      content.hook,
      content.caption,
      content.hashtags.join(' '),
      content.callToAction,
    ].where((section) => section.trim().isNotEmpty).join('\n\n');
  }

  @override
  Widget build(BuildContext context) {
    final result = MiniBossEngine.analyze(widget.product);
    final generatedContent = _generatedContent;

    return AlertDialog(
      title: Row(
        children: [
          const Icon(Icons.smart_toy),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              widget.product.name,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Column(
                children: [
                  const Text(
                    'MiniBoss Score',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '${result.score}/100',
                    style: const TextStyle(
                      fontSize: 30,
                      fontWeight: FontWeight.bold,
                      color: Colors.green,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            const Divider(),
            const Text(
              'Reasons',
              style: TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            ...result.reasons.map(
              (reason) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(reason),
              ),
            ),
            const Divider(),
            ListTile(
              dense: true,
              leading: const Icon(Icons.speed),
              title: const Text('Difficulty'),
              subtitle: Text(result.difficulty),
            ),
            ListTile(
              dense: true,
              leading: const Icon(Icons.groups),
              title: const Text('Competition'),
              subtitle: Text(result.competition),
            ),
            ListTile(
              dense: true,
              leading: const Icon(Icons.local_fire_department),
              title: const Text('Viral Chance'),
              subtitle: Text(result.viralChance),
            ),
            ListTile(
              dense: true,
              leading: const Icon(Icons.workspace_premium),
              title: const Text('Recommendation'),
              subtitle: Text(result.recommendation),
            ),
            ListTile(
              dense: true,
              leading: const Icon(Icons.bolt),
              title: const Text('Action'),
              subtitle: Text(result.action),
            ),
            if (generatedContent != null) ...[
              const Divider(),
              const SizedBox(height: 8),
              Text(
                '✨ AI Preview',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 12),
              _ContentCard(
                icon: Icons.campaign,
                title: 'Hook',
                child: Text(generatedContent.hook),
              ),
              _ContentCard(
                icon: Icons.notes,
                title: 'Caption',
                action: TextButton.icon(
                  onPressed: () => _copyText(
                    generatedContent.caption,
                    'Caption copied',
                  ),
                  icon: const Icon(Icons.copy),
                  label: const Text('Copy Caption'),
                ),
                child: Text(generatedContent.caption),
              ),
              _ContentCard(
                icon: Icons.tag,
                title: 'Hashtags',
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: generatedContent.hashtags.map((tag) {
                    return Chip(label: Text(tag));
                  }).toList(),
                ),
              ),
              _ContentCard(
                icon: Icons.call_made,
                title: 'Call To Action',
                child: Text(generatedContent.callToAction),
              ),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.tonalIcon(
                  onPressed: () => _copyText(
                    _buildPostText(generatedContent),
                    'Post copied',
                  ),
                  icon: const Icon(Icons.copy_all),
                  label: const Text('Copy Post'),
                ),
              ),
            ],
          ],
        ),
      ),
      actions: [
        FilledButton.icon(
          onPressed: _loading ? null : _generateContent,
          icon: _loading
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.auto_awesome),
          label: Text(_loading ? 'Generating...' : 'Generate AI'),
        ),
        FilledButton.icon(
          onPressed: _loading ? null : () => Navigator.pop(context),
          icon: const Icon(Icons.check),
          label: const Text('Close'),
        ),
      ],
    );
  }
}

class _ContentCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final Widget child;
  final Widget? action;

  const _ContentCard({
    required this.icon,
    required this.title,
    required this.child,
    this.action,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                ),
                if (action != null) action!,
              ],
            ),
            const SizedBox(height: 8),
            child,
          ],
        ),
      ),
    );
  }
}
