import '../../ai/platforms.dart';
import '../../models/affiliate_product.dart';
import '../../models/content_brief.dart';
import '../../models/generated_content.dart';

/// Shared context passed from the product/content workflow into creative
/// prompt services.
///
/// Phase A3 deliberately keeps provider-specific concerns out of this model.
/// Asset providers consume prompts built from this context later in the flow.
class PromptContext {
  final AffiliateProduct product;
  final ContentBrief? brief;
  final PlatformType? platform;
  final GeneratedContent? generatedContent;

  const PromptContext({
    required this.product,
    this.brief,
    this.platform,
    this.generatedContent,
  });

  String get title => product.title;

  String get shop => product.shopName;

  String get price => product.priceText;

  String get sold => product.soldText;

  double get score => product.miniBossScore;

  String get description => product.description ?? '';

  List<String> get tags => product.tags;

  List<String> get keywords => product.keywords;

  String get audience => product.targetAudience ?? '';

  String get mood => product.mood ?? '';

  String get goal => brief?.goal ?? '';

  String get angle => brief?.angle ?? '';

  String get tone => brief?.tone ?? '';

  String get platformName => platform?.displayName ?? '';

  String get hook => generatedContent?.hook ?? '';

  String get caption => generatedContent?.caption ?? '';

  String get callToAction => generatedContent?.callToAction ?? '';

  List<String> get hashtags => generatedContent?.hashtags ?? const [];

  bool get hasCampaignContext =>
      brief != null || platform != null || generatedContent?.isNotEmpty == true;
}
