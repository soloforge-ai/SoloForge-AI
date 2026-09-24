import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/theme/app_theme.dart';
import '../models/affiliate_program.dart';
import '../services/affiliate_agent_service.dart';
import 'affiliate_content_factory_page.dart';

class AffiliateAgentPage extends StatefulWidget {
  const AffiliateAgentPage({super.key, this.service});

  final AffiliateAgentService? service;

  @override
  State<AffiliateAgentPage> createState() => _AffiliateAgentPageState();
}

class _AffiliateAgentPageState extends State<AffiliateAgentPage> {
  late final AffiliateAgentService _service;

  final _searchController = TextEditingController(text: 'AI');
  final _nicheController = TextEditingController(text: 'AI Creator Tools');
  final _audienceController = TextEditingController(
    text: 'creators using AI tools for content, automation, and online income',
  );

  List<AffiliateProgram> _programs = const [];
  Set<String> _savedSlugs = {};
  final Map<String, AffiliateOpportunityScore> _scores = {};
  final Set<String> _analyzing = {};

  bool _loading = false;
  bool _recurringOnly = false;
  bool _verifiedOnly = false;
  int _minCookieDays = 0;
  String? _error;

  @override
  void initState() {
    super.initState();
    _service = widget.service ?? AffiliateAgentService();
    _loadSaved();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _nicheController.dispose();
    _audienceController.dispose();
    if (widget.service == null) {
      _service.dispose();
    }
    super.dispose();
  }

  Future<void> _loadSaved() async {
    final saved = await _service.readSavedPrograms();
    if (!mounted) return;
    setState(() => _savedSlugs = saved.map((item) => item.slug).toSet());
  }

  Future<void> _search() async {
    FocusScope.of(context).unfocus();
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final programs = await _service.searchPrograms(
        query: _searchController.text,
        recurringOnly: _recurringOnly,
        verifiedOnly: _verifiedOnly,
        minCookieDays: _minCookieDays == 0 ? null : _minCookieDays,
      );
      if (!mounted) return;
      setState(() => _programs = programs);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _analyze(AffiliateProgram program) async {
    setState(() => _analyzing.add(program.slug));
    try {
      final score = await _service.analyzeProgram(
        slug: program.slug,
        niche: _nicheController.text,
        audience: _audienceController.text,
      );
      if (!mounted) return;
      setState(() => _scores[program.slug] = score);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString())),
      );
    } finally {
      if (mounted) setState(() => _analyzing.remove(program.slug));
    }
  }

  Future<void> _toggleSaved(AffiliateProgram program) async {
    final isSaved = _savedSlugs.contains(program.slug);
    if (isSaved) {
      await _service.removeSavedProgram(program.slug);
    } else {
      await _service.saveProgram(program);
    }
    if (!mounted) return;
    setState(() {
      if (isSaved) {
        _savedSlugs.remove(program.slug);
      } else {
        _savedSlugs.add(program.slug);
      }
    });
  }

  void _openContentFactory(AffiliateProgram program) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => AffiliateContentFactoryPage(
          program: program,
          niche: _nicheController.text.trim(),
          audience: _audienceController.text.trim(),
        ),
      ),
    );
  }

  Future<void> _openSignup(AffiliateProgram program) async {
    final raw = program.signupUrl ?? program.website;
    if (raw == null || raw.isEmpty) return;
    final uri = Uri.tryParse(raw);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Affiliate Agent'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(
              child: Text(
                'Saved ${_savedSlugs.length}',
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AshColors.indigoMist,
                ),
              ),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          _searchPanel(),
          if (_loading) const LinearProgressIndicator(minHeight: 2),
          Expanded(
            child: _error != null
                ? _errorState()
                : _programs.isEmpty
                    ? _emptyState()
                    : ListView.separated(
                        padding: const EdgeInsets.fromLTRB(12, 10, 12, 24),
                        itemCount: _programs.length,
                        separatorBuilder: (_, _) => const SizedBox(height: 8),
                        itemBuilder: (_, index) => _programCard(_programs[index]),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _searchPanel() {
    return Material(
      color: AshColors.blackPlum,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Column(
          children: [
            TextField(
              controller: _searchController,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _search(),
              decoration: const InputDecoration(
                labelText: 'Find affiliate programs',
                hintText: 'AI video, automation, email...',
                prefixIcon: Icon(Icons.search),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: FilterChip(
                    selected: _recurringOnly,
                    label: const Text('Recurring'),
                    onSelected: (value) =>
                        setState(() => _recurringOnly = value),
                  ),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: FilterChip(
                    selected: _verifiedOnly,
                    label: const Text('Verified'),
                    onSelected: (value) =>
                        setState(() => _verifiedOnly = value),
                  ),
                ),
                const SizedBox(width: 6),
                DropdownButton<int>(
                  value: _minCookieDays,
                  items: const [
                    DropdownMenuItem(value: 0, child: Text('Any cookie')),
                    DropdownMenuItem(value: 30, child: Text('30d+')),
                    DropdownMenuItem(value: 60, child: Text('60d+')),
                    DropdownMenuItem(value: 90, child: Text('90d+')),
                  ],
                  onChanged: (value) =>
                      setState(() => _minCookieDays = value ?? 0),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _nicheController,
                    decoration: const InputDecoration(
                      labelText: 'Niche for scoring',
                      isDense: true,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _audienceController,
                    decoration: const InputDecoration(
                      labelText: 'Audience',
                      isDense: true,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _loading ? null : _search,
                icon: const Icon(Icons.travel_explore),
                label: const Text('Discover Opportunities'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _programCard(AffiliateProgram program) {
    final score = _scores[program.slug];
    final saved = _savedSlugs.contains(program.slug);
    final analyzing = _analyzing.contains(program.slug);

    return Card(
      margin: EdgeInsets.zero,
      child: ExpansionTile(
        leading: CircleAvatar(
          backgroundColor: AshColors.blackPlum,
          child: Text(
            program.name.isEmpty ? '?' : program.name[0].toUpperCase(),
            style: const TextStyle(
              color: AshColors.indigoMist,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
        title: Text(
          program.name,
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Text(
          [
            if (program.category != null) program.category!,
            program.commissionLabel,
            if (program.cookieDays != null) '${program.cookieDays}d cookie',
            program.verified ? 'verified' : 'unverified',
          ].join(' • '),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: score == null
            ? Icon(saved ? Icons.bookmark : Icons.bookmark_border)
            : _ScoreBadge(score: score.totalScore),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              program.shortDescription ??
                  program.description ??
                  'No description supplied.',
            ),
          ),
          if (program.restrictions != null) ...[
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Restrictions: ${program.restrictions}',
                style: const TextStyle(color: Colors.orangeAccent),
              ),
            ),
          ],
          if (score != null) ...[
            const SizedBox(height: 12),
            _analysisView(score),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.tonalIcon(
                onPressed: analyzing ? null : () => _analyze(program),
                icon: analyzing
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.analytics_outlined),
                label: Text(score == null ? 'Analyze' : 'Analyze again'),
              ),
              OutlinedButton.icon(
                onPressed: () => _toggleSaved(program),
                icon: Icon(saved ? Icons.bookmark : Icons.bookmark_border),
                label: Text(saved ? 'Saved' : 'Save'),
              ),
              FilledButton.icon(
                onPressed: () => _openContentFactory(program),
                icon: const Icon(Icons.auto_awesome),
                label: const Text('Create Content'),
              ),
              if (program.signupUrl != null || program.website != null)
                TextButton.icon(
                  onPressed: () => _openSignup(program),
                  icon: const Icon(Icons.open_in_new),
                  label: const Text('Program page'),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _analysisView(AffiliateOpportunityScore score) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AshColors.blackPlum,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: AshColors.indigoMist.withValues(alpha: 0.4),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _ScoreBadge(score: score.totalScore),
              const SizedBox(width: 8),
              const Text(
                'Opportunity Score',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Audience ${score.audienceFit.toStringAsFixed(0)} • '
            'Content ${score.contentPotential.toStringAsFixed(0)} • '
            'Commission ${score.commissionScore.toStringAsFixed(0)}',
            style: const TextStyle(
              fontSize: 12,
              color: AshColors.smokeSilver,
            ),
          ),
          if (score.rationale.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...score.rationale.take(3).map(
                  (item) => Text('• $item', style: const TextStyle(fontSize: 12)),
                ),
          ],
          if (score.risks.isNotEmpty) ...[
            const SizedBox(height: 8),
            const Text(
              'Check before promoting',
              style: TextStyle(
                fontWeight: FontWeight.w800,
                color: Colors.orangeAccent,
              ),
            ),
            ...score.risks.take(3).map(
                  (item) => Text('• $item', style: const TextStyle(fontSize: 12)),
                ),
          ],
          if (score.contentAngles.isNotEmpty) ...[
            const SizedBox(height: 8),
            const Text(
              'Content angles',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
            ...score.contentAngles.take(3).map(
                  (item) => Text('• $item', style: const TextStyle(fontSize: 12)),
                ),
          ],
        ],
      ),
    );
  }

  Widget _emptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Text(
          'ค้นหาโปรแกรม Affiliate แล้วให้ SoloForge วิเคราะห์ว่า '
          'ตัวไหนเหมาะกับ niche และ audience ของเราก่อนลงแรงทำคอนเทนต์',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: AshColors.smokeSilver.withValues(alpha: 0.9),
          ),
        ),
      ),
    );
  }

  Widget _errorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 36),
            const SizedBox(height: 8),
            Text(_error!, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: _search,
              child: const Text('Try again'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ScoreBadge extends StatelessWidget {
  const _ScoreBadge({required this.score});

  final double score;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 48),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: AshColors.indigoMist.withValues(alpha: 0.18),
        border: Border.all(color: AshColors.indigoMist),
      ),
      child: Text(
        score.toStringAsFixed(0),
        textAlign: TextAlign.center,
        style: const TextStyle(
          color: AshColors.boneWhite,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}
