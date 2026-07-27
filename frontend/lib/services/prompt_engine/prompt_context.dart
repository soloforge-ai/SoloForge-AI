import '../../models/affiliate_product.dart';

class PromptContext {
  final AffiliateProduct product;

  const PromptContext({required this.product});

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
}
