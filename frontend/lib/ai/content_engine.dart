import '../models/product.dart';
import 'platforms.dart';
import 'prompt_builder.dart';

class ContentEngine {
  const ContentEngine._();

  static Future<String> generateCaption({
    required Product product,
    required PlatformType platform,
  }) async {
    final prompt = PromptBuilder.buildCaptionPrompt(
      product: product,
      platform: platform,
    );

    // TODO:
    // เปลี่ยนส่วนนี้เป็นการเรียก OpenAI / Gemini / OpenRouter ในอนาคต

    return '''
=== MOCK AI RESPONSE ===

Platform : ${platform.displayName}

Product : ${product.name}

Generated from PromptBuilder.

----------------------------------------

$prompt
''';
  }
}