class ImagePrompt {
  final String positivePrompt;
  final String negativePrompt;

  final Map<String, dynamic> metadata;

  const ImagePrompt({
    required this.positivePrompt,
    required this.negativePrompt,
    required this.metadata,
  });
}