class ModelBenchmarkResult {
  final String benchmarkId;
  final String runId;
  final String provider;
  final String modelId;
  final String promptId;
  final List<String> referenceIds;
  final Map<String, dynamic> parameters;
  final String? assetUrl;
  final DateTime createdAt;
  final int? durationMs;
  final double? estimatedCost;
  final Map<String, double> qualityScores;
  final double? overallScore;
  final String status;
  final String? error;

  const ModelBenchmarkResult({
    required this.benchmarkId,
    required this.runId,
    required this.provider,
    required this.modelId,
    required this.promptId,
    required this.referenceIds,
    required this.parameters,
    required this.assetUrl,
    required this.createdAt,
    required this.durationMs,
    required this.estimatedCost,
    required this.qualityScores,
    required this.overallScore,
    required this.status,
    required this.error,
  });

  bool get isSuccess => status == 'success';
}
