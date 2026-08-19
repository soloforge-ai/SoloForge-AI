import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/ai/platforms.dart';
import 'package:frontend/ai/prompt_builder.dart';
import 'package:frontend/models/content_brief.dart';
import 'package:frontend/models/product.dart';

void main() {
  test('prompt includes the selected content brief', () {
    final product = Product(
      id: 1,
      name: 'Test Bag',
      price: 990,
      commission: 10,
      rating: 4.8,
      category: 'Travel',
      shop: 'Test Shop',
      targetAudience: 'Frequent travelers',
    );

    const brief = ContentBrief(
      goal: 'Sell',
      angle: 'Problem → Solution',
      tone: 'Premium',
    );

    final prompt = PromptBuilder.buildCaptionPrompt(
      product: product,
      platform: PlatformType.tiktok,
      brief: brief,
    );

    expect(prompt, contains('Goal: Sell'));
    expect(prompt, contains('Selling Angle: Problem → Solution'));
    expect(prompt, contains('Tone: Premium'));
  });
}
