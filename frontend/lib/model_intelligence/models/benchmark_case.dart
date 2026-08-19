class BenchmarkCase {
  final String id;
  final String name;
  final String description;
  final String prompt;
  final List<String> referenceIds;
  final int width;
  final int height;
  final int? seed;

  const BenchmarkCase({
    required this.id,
    required this.name,
    required this.description,
    required this.prompt,
    this.referenceIds = const [],
    this.width = 1024,
    this.height = 1024,
    this.seed,
  });
}
