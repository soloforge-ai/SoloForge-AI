import '../models/generated_content.dart';
import '../models/product.dart';
import 'platforms.dart';
import 'prompt_builder.dart';

class ContentEngine {
  const ContentEngine._();

  static Future<GeneratedContent> generateContent({
    required Product product,
    required PlatformType platform,
  }) async {
    final prompt = PromptBuilder.buildCaptionPrompt(
      product: product,
      platform: platform,
    );

    // TODO:
    // ส่ง prompt ไปยัง OpenAI / Gemini / OpenRouter

    return GeneratedContent(
      title: '${product.name} รีวิว',
      hook: 'หยุดเลื่อนก่อน! ตัวนี้น่าสนใจกว่าที่คิด 👀',
      caption: '''
นี่คือ Mock Content ที่สร้างจาก PromptBuilder

สินค้า : ${product.name}
ราคา : ฿${product.price}
หมวดหมู่ : ${product.category}

Prompt Length : ${prompt.length} characters
''',
      hashtags: const [
        '#SoloForgeAI',
        '#Affiliate',
        '#AIContent',
      ],
      callToAction: 'กดดูรายละเอียดเพิ่มเติมได้เลย ✨',
      platform: platform,
      createdAt: DateTime.now(),
    );
  }
}