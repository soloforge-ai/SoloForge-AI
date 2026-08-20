import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/ai/platforms.dart';
import 'package:frontend/models/affiliate_product.dart';
import 'package:frontend/models/content_brief.dart';
import 'package:frontend/models/generated_content.dart';
import 'package:frontend/services/prompt_engine/image_prompt_service.dart';
import 'package:frontend/services/prompt_engine/prompt_context.dart';

void main() {
  test('image prompt includes product, brief, platform, and generated content', () {
    final product = AffiliateProduct.fromJson({
      'id': '101',
      'title': 'Travel Bag',
      'price': 990,
      'sold': 150,
      'category': 'Travel',
      'shop': {'name': 'Solo Shop'},
      'commission': {'rate': 0.1, 'amount': 99},
      'links': {'product': '', 'affiliate': ''},
      'images': <String>[],
      'miniboss': {'score': 88},
      'description': 'Lightweight carry-on bag',
      'keywords': ['lightweight', 'travel'],
      'tags': ['bag'],
      'targetAudience': 'Frequent travelers',
      'mood': 'Clean',
    });

    const brief = ContentBrief(
      goal: 'Sell',
      angle: 'Problem → Solution',
      tone: 'Premium',
    );

    final content = GeneratedContent(
      title: 'Travel smarter',
      hook: 'Still carrying a heavy bag?',
      caption: 'Travel lighter with a compact carry-on.',
      hashtags: const ['#Travel', '#CarryOn'],
      callToAction: 'Shop now',
      platform: PlatformType.tiktok,
      createdAt: DateTime(2026, 8, 20),
    );

    final context = PromptContext(
      product: product,
      brief: brief,
      platform: PlatformType.tiktok,
      generatedContent: content,
    );

    final prompt = const ImagePromptService().buildProductPrompt(context);

    expect(prompt, contains('Product: Travel Bag'));
    expect(prompt, contains('Goal: Sell'));
    expect(prompt, contains('Selling Angle: Problem → Solution'));
    expect(prompt, contains('Tone: Premium'));
    expect(prompt, contains('Platform: TikTok'));
    expect(prompt, contains('Hook: Still carrying a heavy bag?'));
    expect(prompt, contains('Call To Action: Shop now'));
    expect(prompt, contains('#Travel #CarryOn'));
  });
}
