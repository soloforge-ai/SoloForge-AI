import '../models/product.dart';
import 'platforms.dart';
import 'templates.dart';

class PromptBuilder {
  const PromptBuilder._();

  static String buildCaptionPrompt({
    required Product product,
    required PlatformType platform,
  }) {
    final template = _getTemplate(platform);

    return '''
$template

==============================
Product Information
==============================

Name: ${product.name}
Category: ${product.category}
Brand: ${product.brand ?? "-"}
Shop: ${product.shop}

Price: ${product.price}
Commission: ${product.commission}%
Rating: ${product.rating}

==============================
Target Audience
==============================

${product.targetAudience ?? "-"}

==============================
Product Metadata
==============================

Description:
${product.description ?? "-"}

Tags:
${product.tags.isEmpty ? "-" : product.tags.join(", ")}

Keywords:
${product.keywords.isEmpty ? "-" : product.keywords.join(", ")}

Mood:
${product.mood ?? "-"}

==============================
MiniBoss Analysis
==============================

Evergreen:
${product.evergreen}

Giftable:
${product.giftable}

Suitable For Short Video:
${product.suitableForShortVideo}

CEO Approved:
${product.ceoApproved}

==============================
Instructions
==============================

Write high-quality affiliate marketing content.

Requirements:

- Focus on the product benefits.
- Use the product metadata as the primary context.
- Naturally use the provided keywords.
- Match the writing style for the selected platform.
- Do not invent product features.
- Keep the content engaging and persuasive.
- Avoid generic marketing phrases.
- End with a clear call-to-action.

Generate the best possible content.
''';
  }

  static String _getTemplate(PlatformType platform) {
    switch (platform) {
      case PlatformType.tiktok:
        return PromptTemplates.tiktokCaption;

      case PlatformType.facebook:
        return PromptTemplates.facebookCaption;

      case PlatformType.instagram:
        return PromptTemplates.facebookCaption;

      case PlatformType.lemon8:
        return PromptTemplates.lemon8Caption;

      case PlatformType.youtube:
        return PromptTemplates.youtubeShortScript;

      case PlatformType.x:
        return PromptTemplates.facebookCaption;
    }
  }
}