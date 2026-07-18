import 'package:flutter/material.dart';

import '../engine/miniboss_engine.dart';
import '../models/generated_content.dart';
import '../models/product.dart';

import '../ai/content_engine.dart';
import '../ai/platforms.dart';

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

  @override
  Widget build(BuildContext context) {
    final result = MiniBossEngine.analyze(widget.product);

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
                    "MiniBoss Score",
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "${result.score}/100",
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
              "Reasons",
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
              title: const Text("Difficulty"),
              subtitle: Text(result.difficulty),
            ),
            ListTile(
              dense: true,
              leading: const Icon(Icons.groups),
              title: const Text("Competition"),
              subtitle: Text(result.competition),
            ),
            ListTile(
              dense: true,
              leading: const Icon(Icons.local_fire_department),
              title: const Text("Viral Chance"),
              subtitle: Text(result.viralChance),
            ),
            ListTile(
              dense: true,
              leading: const Icon(Icons.workspace_premium),
              title: const Text("Recommendation"),
              subtitle: Text(result.recommendation),
            ),
            ListTile(
              dense: true,
              leading: const Icon(Icons.bolt),
              title: const Text("Action"),
              subtitle: Text(result.action),
            ),

// 👇 วางตรงนี้
if (_generatedContent != null) ...[
  const Divider(),
  const SizedBox(height: 8),

  const Text(
    '✨ AI Generated Content',
    style: TextStyle(
      fontSize: 16,
      fontWeight: FontWeight.bold,
    ),
  ),

  const SizedBox(height: 12),

  Card(
  margin: const EdgeInsets.only(bottom: 12),
  child: Padding(
    padding: const EdgeInsets.all(12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.campaign, size: 18),
            const SizedBox(width: 8),
            Text(
              'Hook',
              style: Theme.of(context).textTheme.titleSmall,
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(_generatedContent!.hook),
      ],
    ),
  ),
),

  const SizedBox(height: 12),

  Text(
    'Caption',
    style: Theme.of(context).textTheme.titleSmall,
  ),
  Text(_generatedContent!.caption),

  const SizedBox(height: 12),

  Text(
  'Hashtags',
  style: Theme.of(context).textTheme.titleSmall,
),
const SizedBox(height: 8),
Wrap(
  spacing: 8,
  runSpacing: 8,
  children: _generatedContent!.hashtags.map((tag) {
    return Chip(
      label: Text(tag),
    );
  }).toList(),
),

  const SizedBox(height: 12),

  Text(
    'Call To Action',
    style: Theme.of(context).textTheme.titleSmall,
  ),
  Text(_generatedContent!.callToAction),
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
            child: CircularProgressIndicator(
              strokeWidth: 2,
            ),
          )
        : const Icon(Icons.auto_awesome),
    label: Text(
      _loading
          ? "Generating..."
          : "Generate AI",
    ),
  ),

  FilledButton.icon(
    onPressed: _loading ? null : () => Navigator.pop(context),
    icon: const Icon(Icons.check),
    label: const Text("Close"),
  ),
],
    );
  }
}