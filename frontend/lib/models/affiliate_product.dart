import 'product.dart';

/// Represents a product from the Shopee master affiliate catalog.
class AffiliateProduct {
  /// Creates a Shopee affiliate product entity.
  const AffiliateProduct({
    required this.itemId,
    required this.title,
    required this.price,
    required this.sold,
    required this.shopName,
    required this.commissionRate,
    required this.commissionAmount,
    required this.productUrl,
    required this.affiliateUrl,
    required this.priceBucket,
    required this.priceScore,
    required this.soldBucket,
    required this.soldScore,
    required this.commissionBucket,
    required this.commissionScore,
    required this.miniBossScore,
  });

  final String itemId;
  final String title;
  final double price;
  final int sold;
  final String shopName;
  final double commissionRate;
  final double commissionAmount;
  final String productUrl;
  final String affiliateUrl;
  final String priceBucket;
  final double priceScore;
  final String soldBucket;
  final double soldScore;
  final String commissionBucket;
  final double commissionScore;
  final double miniBossScore;

  factory AffiliateProduct.fromCsv(Map<String, String> row) {
    return AffiliateProduct(
      itemId: _read(row, 'itemId'),
      title: _read(row, 'title'),
      price: _readDouble(row, 'price'),
      sold: _readInt(row, 'sold'),
      shopName: _read(row, 'shopName'),
      commissionRate: _readDouble(row, 'commissionRate'),
      commissionAmount: _readDouble(row, 'commissionAmount'),
      productUrl: _read(row, 'productUrl'),
      affiliateUrl: _read(row, 'affiliateUrl'),
      priceBucket: _read(row, 'PriceBucket'),
      priceScore: _readDouble(row, 'PriceScore'),
      soldBucket: _read(row, 'SoldBucket'),
      soldScore: _readDouble(row, 'SoldScore'),
      commissionBucket: _read(row, 'CommissionBucket'),
      commissionScore: _readDouble(row, 'CommissionScore'),
      miniBossScore: _readDouble(row, 'MiniBossScore'),
    );
  }

  Product toProduct() {
    return Product(
      id: int.tryParse(itemId) ?? itemId.hashCode,
      name: title,
      price: price.round(),
      commission: commissionAmount.round(),
      rating: (miniBossScore / 20).clamp(0, 5).toDouble(),
      category: priceBucket,
      shop: shopName,
      brand: shopName,
    );
  }

  static String _read(Map<String, String> row, String key) => row[key]?.trim() ?? '';

  static double _readDouble(Map<String, String> row, String key) {
    final value = _read(row, key).replaceAll(',', '').replaceAll('%', '');
    return double.tryParse(value) ?? 0;
  }

  static int _readInt(Map<String, String> row, String key) {
    final value = _read(row, key).replaceAll(',', '');
    return int.tryParse(value) ?? double.tryParse(value)?.round() ?? 0;
  }
}
