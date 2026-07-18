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

Product Information

Name: ${product.name}
Category: ${product.category}
Brand: ${product.brand ?? "-"}
Price: ${product.price}
Rating: ${product.rating}
Commission: ${product.commission}%

Target Audience: ${product.targetAudience ?? "-"}

MiniBoss Notes

Evergreen: ${product.evergreen}
Giftable: ${product.giftable}

Generate high-quality content based on this product.
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