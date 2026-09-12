import 'package:flutter/material.dart';

import '../models/ai_model.dart';
import '../services/model_catalog_service.dart';

class ModelIntelligencePage extends StatefulWidget {
  const ModelIntelligencePage({super.key});

  @override
  State<ModelIntelligencePage> createState() => _ModelIntelligencePageState();
}

class _ModelIntelligencePageState extends State<ModelIntelligencePage> {
  final _service = ModelCatalogService();
  final _searchController = TextEditingController();
  List<AiModel> _models = const [];
  String _filter = 'All';
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
      final models = await _service.fetchAllModels();
      if (!mounted) return;
      setState(() {
        _models = models;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = '$error';
      });
    }
  }

  List<AiModel> get _visibleModels {
    final query = _searchController.text.trim().toLowerCase();
    return _models.where((model) {
      final matchesSearch = query.isEmpty ||
          model.id.toLowerCase().contains(query) ||
          model.name.toLowerCase().contains(query) ||
          model.provider.toLowerCase().contains(query);
      final matchesFilter = _filter == 'All' ||
          model.modalities.any((m) => _label(m) == _filter);
      return matchesSearch && matchesFilter;
    }).toList();
  }

  String _label(AiModelModality modality) => switch (modality) {
        AiModelModality.text => 'Text',
        AiModelModality.image => 'Image',
        AiModelModality.video => 'Video',
        AiModelModality.audio => 'Audio',
        AiModelModality.embedding => 'Embedding',
        AiModelModality.threeD => '3D',
        AiModelModality.realtime => 'Realtime',
        AiModelModality.unknown => 'Other',
      };

  @override
  void dispose() {
    _searchController.dispose();
    _service.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final models = _visibleModels;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Model Intelligence'),
        actions: [
          IconButton(
            tooltip: 'Refresh model catalog',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Column(
        children: [
          _buildHeader(),
          if (_error != null) _buildError(),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : models.isEmpty
                    ? const Center(child: Text('No models found.'))
                    : ListView.separated(
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                        itemCount: models.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, index) => _ModelCard(model: models[index]),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    final counts = <String, int>{};
    for (final model in _models) {
      for (final modality in model.modalities) {
        final label = _label(modality);
        counts[label] = (counts[label] ?? 0) + 1;
      }
    }

    final filters = ['All', ...counts.keys.toList()..sort()];

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'AI Model Catalog',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 4),
          Text('${_models.length} models • live catalog • no API key required'),
          const SizedBox(height: 12),
          TextField(
            controller: _searchController,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Search model, provider, or ID',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: filters.map((filter) {
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(filter),
                    selected: _filter == filter,
                    onSelected: (_) => setState(() => _filter = filter),
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildError() => MaterialBanner(
        content: Text(_error!),
        leading: const Icon(Icons.error_outline),
        actions: [
          TextButton(onPressed: _load, child: const Text('Retry')),
        ],
      );
}

class _ModelCard extends StatelessWidget {
  final AiModel model;

  const _ModelCard({required this.model});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    model.name,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                if (model.community)
                  const Chip(
                    label: Text('Community'),
                    avatar: Icon(Icons.people_outline, size: 16),
                  ),
              ],
            ),
            const SizedBox(height: 2),
            Text(model.id, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: model.modalities
                  .map((modality) => Chip(label: Text(_label(modality))))
                  .toList(),
            ),
            if (model.capabilities.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text('Capabilities: ${model.capabilities.keys.join(', ')}'),
            ],
          ],
        ),
      ),
    );
  }

  String _label(AiModelModality modality) => switch (modality) {
        AiModelModality.text => 'Text',
        AiModelModality.image => 'Image',
        AiModelModality.video => 'Video',
        AiModelModality.audio => 'Audio',
        AiModelModality.embedding => 'Embedding',
        AiModelModality.threeD => '3D',
        AiModelModality.realtime => 'Realtime',
        AiModelModality.unknown => 'Other',
      };
}
