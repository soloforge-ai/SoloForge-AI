import '../models/benchmark_case.dart';
import '../models/model_benchmark_result.dart';

/// Provider-neutral benchmark orchestration contract.
///
/// The service deliberately does not contain API-key handling or a concrete
/// Pollinations implementation. A provider adapter can be injected later.
abstract class ImageBenchmarkProvider {
  Future<ModelBenchmarkResult> generate({
    required BenchmarkCase benchmarkCase,
    required String runId,
    required String modelId,
  });
}

class ImageBenchmarkService {
  final ImageBenchmarkProvider provider;

  const ImageBenchmarkService({required this.provider});

  Future<List<ModelBenchmarkResult>> run({
    required BenchmarkCase benchmarkCase,
    required List<String> modelIds,
    required String runId,
  }) async {
    final results = <ModelBenchmarkResult>[];

    for (final modelId in modelIds) {
      results.add(
        await provider.generate(
          benchmarkCase: benchmarkCase,
          runId: runId,
          modelId: modelId,
        ),
      );
    }

    return results;
  }
}
