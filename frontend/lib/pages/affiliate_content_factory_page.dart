import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/theme/app_theme.dart';
import '../models/affiliate_content_package.dart';
import '../models/affiliate_program.dart';
import '../services/affiliate_agent_service.dart';

class AffiliateContentFactoryPage extends StatefulWidget {
  const AffiliateContentFactoryPage({
    super.key,
    required this.program,
    required this.niche,
    required this.audience,
  });

  final AffiliateProgram program;
  final String niche;
  final String audience;

  @override
  State<AffiliateContentFactoryPage> createState() =>
      _AffiliateContentFactoryPageState();
}

class _AffiliateContentFactoryPageState
    extends State<AffiliateContentFactoryPage> {
  final AffiliateAgentService _service = AffiliateAgentService();
  final _affiliateUrlController = TextEditingController();

  String _platform = 'youtube_shorts';
  String _format = 'review';
  String _intent = 'commercial_investigation';
  String _goal = 'affiliate_click';
  bool _loading = false;
  String? _error;
  AffiliateContentPackage? _package;

  @override
  void dispose() {
    _affiliateUrlController.dispose();
    _service.dispose();
    super.dispose();
  }

  Future<void> _generate() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final result = await _service.generateContentPackage(
        slug: widget.program.slug,
        platform: _platform,
        format: _format,
        intent: _intent,
        goal: _goal,
        niche: widget.niche,
        audience: widget.audience,
        affiliateUrl: _affiliateUrlController.text,
      );
      if (!mounted) return;
      setState(() => _package = result);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _copyAll() async {
    final package = _package;
    if (package == null) return;
    await Clipboard.setData(ClipboardData(text: package.toCopyableText()));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Content package copied')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Content Factory'),
        actions: [
          if (_package != null)
            IconButton(
              tooltip: 'Copy package',
              onPressed: _copyAll,
              icon: const Icon(Icons.copy_all_outlined),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _programHeader(),
          const SizedBox(height: 14),
          _settings(),
          const SizedBox(height: 14),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null) ...[
            const SizedBox(height: 12),
            _errorCard(),
          ],
          if (_package != null) ...[
            const SizedBox(height: 14),
            _output(_package!),
          ],
        ],
      ),
    );
  }

  Widget _programHeader() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.program.name,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              widget.program.shortDescription ??
                  widget.program.description ??
                  'Affiliate program',
              style: const TextStyle(color: AshColors.smokeSilver),
            ),
            const SizedBox(height: 8),
            Text(
              'Niche: ${widget.niche}\nAudience: ${widget.audience}',
              style: const TextStyle(fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _settings() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: _dropdown(
                    label: 'Platform',
                    value: _platform,
                    values: const {
                      'youtube_shorts': 'YouTube Shorts',
                      'youtube': 'YouTube',
                      'tiktok': 'TikTok',
                      'facebook': 'Facebook',
                    },
                    onChanged: (value) => setState(() => _platform = value),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _dropdown(
                    label: 'Format',
                    value: _format,
                    values: const {
                      'review': 'Review',
                      'tutorial': 'Tutorial',
                      'comparison': 'Comparison',
                      'experiment': 'Experiment',
                    },
                    onChanged: (value) => setState(() => _format = value),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: _dropdown(
                    label: 'Intent',
                    value: _intent,
                    values: const {
                      'commercial_investigation': 'Compare / Evaluate',
                      'tutorial': 'Learn',
                      'purchase': 'Purchase',
                    },
                    onChanged: (value) => setState(() => _intent = value),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _dropdown(
                    label: 'Goal',
                    value: _goal,
                    values: const {
                      'affiliate_click': 'Affiliate Click',
                      'signup': 'Signup',
                      'traffic': 'Traffic',
                    },
                    onChanged: (value) => setState(() => _goal = value),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _affiliateUrlController,
              decoration: const InputDecoration(
                labelText: 'My Affiliate URL (optional)',
                hintText: 'ใส่หลังได้รับอนุมัติโปรแกรม',
                prefixIcon: Icon(Icons.link),
              ),
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _loading ? null : _generate,
                icon: const Icon(Icons.auto_awesome),
                label: const Text('Generate with AI'),
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'ต้องเชื่อม Pollinations ก่อน ระบบจะไม่เขียนว่าทดลองจริงหรือได้ผลจริง '
              'ถ้ายังไม่มีหลักฐาน',
              style: TextStyle(
                fontSize: 11,
                color: AshColors.smokeSilver,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _dropdown({
    required String label,
    required String value,
    required Map<String, String> values,
    required ValueChanged<String> onChanged,
  }) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      decoration: InputDecoration(labelText: label, isDense: true),
      items: values.entries
          .map(
            (entry) => DropdownMenuItem(
              value: entry.key,
              child: Text(entry.value),
            ),
          )
          .toList(),
      onChanged: (next) {
        if (next != null) onChanged(next);
      },
    );
  }

  Widget _errorCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.error_outline, color: Colors.orangeAccent),
            const SizedBox(width: 10),
            Expanded(child: Text(_error!)),
          ],
        ),
      ),
    );
  }

  Widget _output(AffiliateContentPackage package) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _section('Title', [package.title]),
        _section('Hooks', package.hooks),
        _section('Script', [package.script]),
        _section('Shot List', package.shotList),
        _section('Voiceover', [package.voiceover]),
        _section('Visual Prompts', package.visualPrompts),
        _section('Thumbnail', [package.thumbnailBrief]),
        _section('CTA', [package.cta]),
        _section('Description', [package.description]),
        _claims(package),
        _endCard(package),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: _copyAll,
            icon: const Icon(Icons.copy_all_outlined),
            label: const Text('Copy Full Package'),
          ),
        ),
      ],
    );
  }

  Widget _section(String title, List<String> items) {
    final visible = items.where((item) => item.trim().isNotEmpty).toList();
    if (visible.isEmpty) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w900)),
            const SizedBox(height: 7),
            ...visible.map((item) => Padding(
                  padding: const EdgeInsets.only(bottom: 5),
                  child: Text(visible.length > 1 ? '• $item' : item),
                )),
          ],
        ),
      ),
    );
  }

  Widget _claims(AffiliateContentPackage package) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  package.hasUnverifiedClaims
                      ? Icons.warning_amber_rounded
                      : Icons.verified_outlined,
                  color: package.hasUnverifiedClaims
                      ? Colors.orangeAccent
                      : Colors.greenAccent,
                ),
                const SizedBox(width: 8),
                const Text(
                  'Claim Verification',
                  style: TextStyle(fontWeight: FontWeight.w900),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (package.claims.isEmpty)
              const Text('No explicit claims generated.')
            else
              ...package.claims.map(
                (claim) => Padding(
                  padding: const EdgeInsets.only(bottom: 9),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('• ${claim.claimText}'),
                      Text(
                        '${claim.claimType} • ${claim.verificationStatus}',
                        style: const TextStyle(
                          fontSize: 11,
                          color: Colors.orangeAccent,
                        ),
                      ),
                      if (claim.evidenceRequired.isNotEmpty)
                        Text(
                          claim.evidenceRequired,
                          style: const TextStyle(
                            fontSize: 11,
                            color: AshColors.smokeSilver,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _endCard(AffiliateContentPackage package) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              package.endCardHeading,
              style: const TextStyle(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 7),
            ...package.endCardItems.map(
              (item) => Text('${item.role}: ${item.tool}'),
            ),
            const SizedBox(height: 7),
            Text(
              package.endCardClosing,
              style: const TextStyle(
                color: AshColors.indigoMist,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
