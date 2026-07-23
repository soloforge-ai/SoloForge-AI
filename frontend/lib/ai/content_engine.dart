import '../models/generated_content.dart';
import '../models/product.dart';
import 'platforms.dart';
import 'prompt_builder.dart';
import 'providers/ai_provider.dart';

import 'providers/mock_provider.dart';

class ContentEngine {
  const ContentEngine._();

  static final AIProvider _defaultProvider =
    const MockProvider();

  static Future<GeneratedContent> generateContent({
    required Product product,
    required PlatformType platform,
    AIProvider? provider,
  }) async {
    final prompt = PromptBuilder.buildCaptionPrompt(
      product: product,
      platform: platform,
    );

    try {
      return await (provider ?? _defaultProvider).generateContent(
        prompt: prompt,
        platform: platform,
      );
    } on AIProviderException {
      return GeneratedContent.empty(platform);
    } catch (_) {
      return GeneratedContent.empty(platform);
    }
  }
}
