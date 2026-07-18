import '../../models/generated_content.dart';
import '../platforms.dart';

abstract interface class AIProvider {
  Future<GeneratedContent> generateContent({
    required String prompt,
    required PlatformType platform,
  });
}

class AIProviderException implements Exception {
  final String message;
  final Object? cause;

  const AIProviderException(this.message, [this.cause]);

  @override
  String toString() {
    if (cause == null) {
      return 'AIProviderException: $message';
    }

    return 'AIProviderException: $message ($cause)';
  }
}
