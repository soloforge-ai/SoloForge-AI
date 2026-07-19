/// Represents a product that can be promoted through an affiliate platform.
///
/// The model intentionally keeps platform-specific payloads in [rawData] so
/// integrations such as Shopee can preserve source details without leaking
/// those concerns into the rest of the app.
class AffiliateProduct {
  /// Creates an affiliate product entity.
  const AffiliateProduct({
    required this.id,
    required this.title,
    required this.imageUrl,
    required this.affiliateUrl,
    required this.originalUrl,
    required this.price,
    required this.commissionRate,
    required this.category,
    required this.brand,
    required this.rating,
    required this.sold,
    required this.rawData,
  });

  /// Stable product identifier from the affiliate provider.
  final String id;

  /// Display name of the product.
  final String title;

  /// URL for the product image.
  final String imageUrl;

  /// Trackable affiliate URL used for attribution.
  final String affiliateUrl;

  /// Original marketplace URL before affiliate tracking is applied.
  final String originalUrl;

  /// Current product price in the marketplace currency.
  final double price;

  /// Commission percentage offered for this product.
  final double commissionRate;

  /// Product category used for browsing and filtering.
  final String category;

  /// Product brand or seller-provided brand name.
  final String brand;

  /// Average marketplace rating for the product.
  final double rating;

  /// Number of units sold according to the source platform.
  final int sold;

  /// Raw provider payload for future platform-specific use cases.
  final Map<String, dynamic> rawData;
}
