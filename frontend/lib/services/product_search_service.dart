import '../models/affiliate_product.dart';

class ProductSearchService {
  const ProductSearchService();

  List<AffiliateProduct> search(List<AffiliateProduct> products, String query) {
    final keyword = query.trim().toLowerCase();

    if (keyword.isEmpty) {
      return products;
    }

    final results = <_SearchResult>[];

    for (final product in products) {
      final score = _calculateScore(product, keyword);

      if (score > 0) {
        results.add(_SearchResult(product: product, score: score));
      }
    }

    results.sort((a, b) => b.score.compareTo(a.score));

    return results.map((e) => e.product).toList();
  }

  int _calculateScore(AffiliateProduct product, String keyword) {
    var score = 0;

    if (product.title.toLowerCase().contains(keyword)) {
      score += 100;
    }

    if (product.shopName.toLowerCase().contains(keyword)) {
      score += 20;
    }

    if ((product.description ?? "").toLowerCase().contains(keyword)) {
      score += 60;
    }

    if ((product.mood ?? "").toLowerCase().contains(keyword)) {
      score += 30;
    }

    if ((product.targetAudience ?? "").toLowerCase().contains(keyword)) {
      score += 30;
    }

    for (final tag in product.tags) {
      if (tag.toLowerCase().contains(keyword)) {
        score += 50;
      }
    }

    for (final keywordItem in product.keywords) {
      if (keywordItem.toLowerCase().contains(keyword)) {
        score += 40;
      }
    }

    if (product.ceoApproved) {
      score += 5;
    }

    if (product.suitableForShortVideo) {
      score += 5;
    }

    return score;
  }
}

class _SearchResult {
  final AffiliateProduct product;
  final int score;

  const _SearchResult({required this.product, required this.score});
}
