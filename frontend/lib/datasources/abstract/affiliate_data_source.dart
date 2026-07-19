import '../../models/affiliate_product.dart';

/// Contract for affiliate product providers.
///
/// Implementations can target mock data, Shopee, or future affiliate platforms
/// while keeping repositories and features independent of provider details.
abstract interface class AffiliateDataSource {
  /// Returns a list of affiliate products from the backing provider.
  Future<List<AffiliateProduct>> getProducts();

  /// Searches affiliate products by [keyword].
  Future<List<AffiliateProduct>> search(String keyword);
}
