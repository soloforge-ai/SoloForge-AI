import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/benchmark_case.dart';
import '../models/model_benchmark_result.dart';
import '../services/image_benchmark_service.dart';

/// Image generation adapter for Pollinations.
///
/// API credentials are intentionally supplied by the caller at runtime and
/// must never be hard-coded into the Flutter application source.
class PollinationsImageProvider implements ImageBenchmarkProvider {
  final String apiKey;
  final String baseUrl;
  final http.Client client;

  PollinationsImageProvider({
    required this.apiKey,
    this.baseUrl = 'https://gen.pollinations.ai',
    http.Client? client,
  }) : client = client ?? http.Client();

  @override
  Future<ModelBenchmarkResult> generate({
    required BenchmarkCase benchmarkCase,
    required String runId,
    required String modelId,
  }) async {
    final startedAt = DateTime.now();
    final uri = Uri.parse('$baseUrl/image/${Uri.encodeComponent(benchmarkCase.prompt)}')
        .replace(queryParameters: {
      'model': modelId,
      'width': '${benchmarkCase.width}',
      'height': '${benchmarkCase.height}',
      if (benchmarkCase.seed != null) 'seed': '${benchmarkCase.seed}',
      if (benchmarkCase.referenceIds.isNotEmpty)
        'reference': benchmarkCase.referenceIds.join(','),
    });

    try {
      final response = await client.get(
        uri,
        headers: {
          'Authorization': 'Bearer $apiKey',
          'Accept': 'image/*,application/json',
        },
      );

      final durationMs = DateTime.now().difference(startedAt).inMilliseconds;

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return ModelBenchmarkResult(
          benchmarkId: benchmarkCase.id,
          runId: runId,
          provider: 'pollinations',
          modelId: modelId,
          promptId: benchmarkCase.id,
          referenceIds: benchmarkCase.referenceIds,
          parameters: {
            'width': benchmarkCase.width,
            'height': benchmarkCase.height,
            if (benchmarkCase.seed != null) 'seed': benchmarkCase.seed,
          },
          // The initial adapter intentionally returns the generation endpoint
          // rather than copying binary media into the result contract.
          assetUrl: uri.toString(),
          createdAt: startedAt,
          durationMs: durationMs,
          estimatedCost: null,
          qualityScores: const {},
          overallScore: null,
          status: 'success',
          error: null,
        );
      }

      return _failure(
        benchmarkCase: benchmarkCase,
        runId: runId,
        modelId: modelId,
        startedAt: startedAt,
        durationMs: durationMs,
        error: _extractError(response),
      );
    } catch (error) {
      return _failure(
        benchmarkCase: benchmarkCase,
        runId: runId,
        modelId: modelId,
        startedAt: startedAt,
        durationMs: DateTime.now().difference(startedAt).inMilliseconds,
        error: error.toString(),
      );
    }
  }

  ModelBenchmarkResult _failure({
    required BenchmarkCase benchmarkCase,
    required String runId,
    required String modelId,
    required DateTime startedAt,
    required int durationMs,
    required String error,
  }) {
    return ModelBenchmarkResult(
      benchmarkId: benchmarkCase.id,
      runId: runId,
      provider: 'pollinations',
      modelId: modelId,
      promptId: benchmarkCase.id,
      referenceIds: benchmarkCase.referenceIds,
      parameters: {
        'width': benchmarkCase.width,
        'height': benchmarkCase.height,
        if (benchmarkCase.seed != null) 'seed': benchmarkCase.seed,
      },
      assetUrl: null,
      createdAt: startedAt,
      durationMs: durationMs,
      estimatedCost: null,
      qualityScores: const {},
      overallScore: null,
      status: 'error',
      error: error,
    );
  }

  String _extractError(http.Response response) {
    if (response.body.isEmpty) {
      return 'Pollinations request failed with HTTP ${response.statusCode}.';
    }

    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        return decoded['error']?.toString() ??
            decoded['message']?.toString() ??
            'Pollinations request failed with HTTP ${response.statusCode}.';
      }
    } catch (_) {
      // Fall through to the bounded response text below.
    }

    final body = response.body.trim();
    return body.length > 500 ? body.substring(0, 500) : body;
  }
}
