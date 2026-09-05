import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/ai_model.dart';

class ModelCatalogService {
  static const _baseUrl = 'https://gen.pollinations.ai';

  final http.Client _client;

  ModelCatalogService({http.Client? client}) : _client = client ?? http.Client();

  Future<List<AiModel>> fetchModels({bool community = false}) async {
    final uri = Uri.parse('$_baseUrl/models?community=$community');
    final response = await _client.get(uri).timeout(const Duration(seconds: 20));

    if (response.statusCode != 200) {
      throw Exception('Model catalog request failed (${response.statusCode})');
    }

    final decoded = jsonDecode(response.body);
    final List<dynamic> items;

    if (decoded is List) {
      items = decoded;
    } else if (decoded is Map && decoded['data'] is List) {
      items = List<dynamic>.from(decoded['data']);
    } else {
      throw const FormatException('Unexpected model catalog response');
    }

    return items
        .whereType<Map>()
        .map((item) => AiModel.fromJson(Map<String, dynamic>.from(item)))
        .where((model) => model.id.isNotEmpty)
        .toList();
  }

  Future<List<AiModel>> fetchAllModels() async {
    final results = await Future.wait([
      fetchModels(community: false),
      fetchModels(community: true),
    ]);

    final byId = <String, AiModel>{};
    for (final models in results) {
      for (final model in models) {
        byId[model.id] = model;
      }
    }

    final output = byId.values.toList()
      ..sort((a, b) => a.id.toLowerCase().compareTo(b.id.toLowerCase()));
    return output;
  }

  void dispose() => _client.close();
}
