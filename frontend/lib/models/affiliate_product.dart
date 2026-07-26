import 'product.dart';

/// Represents a product from the Shopee master affiliate catalog.
class AffiliateProduct {
  /// Creates a Shopee affiliate product entity.
  const AffiliateProduct({
    required this.itemId,
    required this.title,

    required this.priceDisplay,
    required this.soldDisplay,

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

    // ==========================
    // SoloForge Metadata
    // ==========================

    this.description,
    this.tags = const [],
    this.keywords = const [],
    this.mood,
    this.targetAudience,
    this.suitableForShortVideo = false,
    this.ceoApproved = false,
    this.favorite = false,
  });

  final String itemId;
  final String title;

  /// Display values (UI)
  final String priceDisplay;
  final String soldDisplay;

  /// Numeric values (Analytics / AI)
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

  // =====================================================
  // SoloForge Metadata
  // =====================================================

  final String? description;

  final List<String> tags;

  final List<String> keywords;

  final String? mood;

  final String? targetAudience;

  final bool suitableForShortVideo;

  final bool ceoApproved;

  final bool favorite;

  factory AffiliateProduct.fromCsv(Map<String, String> row) {
    return AffiliateProduct(
      itemId: _read(row, 'รหัสสินค้า'),
      title: _read(row, 'ชื่อสินค้า'),

      priceDisplay: _read(row, 'PriceDisplay'),
      soldDisplay: _read(row, 'SoldDisplay'),

      price: _readDouble(row, 'PriceValue'),
      sold: _readInt(row, 'SoldValue'),

      shopName: _read(row, 'ชื่อร้านค้า'),

      commissionRate: _readDouble(row, 'CommissionRate'),
      commissionAmount: _readDouble(row, 'CommissionAmount'),

      productUrl: _read(row, 'ลิงก์สินค้า'),
      affiliateUrl: _read(row, 'ลิงก์ข้อเสนอ'),

      priceBucket: _read(row, 'PriceBucket'),
      priceScore: _readDouble(row, 'PriceScore'),

      soldBucket: _read(row, 'SoldBucket'),
      soldScore: _readDouble(row, 'SoldScore'),

      commissionBucket: _read(row, 'CommissionBucket'),
      commissionScore: _readDouble(row, 'CommissionScore'),

      miniBossScore: _readDouble(row, 'MiniBossScore'),

      // Metadata
      description: _read(row, 'Description'),

      tags: _split(_read(row, 'Tags')),

      keywords: _split(_read(row, 'Keywords')),

      mood: _read(row, 'Mood').isEmpty
          ? null
          : _read(row, 'Mood'),

      targetAudience: _read(row, 'TargetAudience').isEmpty
          ? null
          : _read(row, 'TargetAudience'),

      suitableForShortVideo:
          _read(row, 'ShortVideo') == 'true',

      ceoApproved:
          _read(row, 'CEOApproved') == 'true',

      favorite:
          _read(row, 'Favorite') == 'true',
    );
  }

  factory AffiliateProduct.fromJson(
      Map<String, dynamic> json,
    ) {
      return AffiliateProduct(
      itemId: json['id']?.toString() ?? '',
      title: json['title'] ?? '',

      priceDisplay:
          (json['sale_price'] ?? json['price'] ?? 0).toString(),

      soldDisplay:
          (json['sold'] ?? 0).toString(),

      price:
          (json['sale_price'] ?? json['price'] ?? 0)
              .toDouble(),

      sold: json['sold'] ?? 0,

      shopName:
          json['shop']?['name'] ?? '',

      commissionRate:
          (json['commission']?['rate'] ?? 0)
              .toDouble(),

      commissionAmount:
          (json['commission']?['amount'] ?? 0)
              .toDouble(),

      productUrl:
          json['links']?['product'] ?? '',

      affiliateUrl:
          json['links']?['short'] ?? '',

      // ยังไม่มีข้อมูลใน catalog.json
      priceBucket: '',
      priceScore: 0,

      soldBucket: '',
      soldScore: 0,

      commissionBucket: '',
      commissionScore: 0,

      miniBossScore:
          (json['miniboss']?['score'] ?? 0)
              .toDouble(),

      description: null,

      tags: const [],

      keywords: const [],

      mood: null,

      targetAudience: null,

      suitableForShortVideo: false,

      ceoApproved: false,

      favorite: false,
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
      description: description,
      tags: tags,
      keywords: keywords,
      mood: mood,
      targetAudience: targetAudience,
      suitableForShortVideo: suitableForShortVideo,
      ceoApproved: ceoApproved,
    );
  }

  AffiliateProduct copyWith({
    String? description,
    List<String>? tags,
    List<String>? keywords,
    String? mood,
    String? targetAudience,
    bool? suitableForShortVideo,
    bool? ceoApproved,
    bool? favorite,
  }) {
    return AffiliateProduct(
      itemId: itemId,
      title: title,
      priceDisplay: priceDisplay,
      soldDisplay: soldDisplay,
      price: price,
      sold: sold,
      shopName: shopName,
      commissionRate: commissionRate,
      commissionAmount: commissionAmount,
      productUrl: productUrl,
      affiliateUrl: affiliateUrl,
      priceBucket: priceBucket,
      priceScore: priceScore,
      soldBucket: soldBucket,
      soldScore: soldScore,
      commissionBucket: commissionBucket,
      commissionScore: commissionScore,
      miniBossScore: miniBossScore,
      description: description ?? this.description,
      tags: tags ?? this.tags,
      keywords: keywords ?? this.keywords,
      mood: mood ?? this.mood,
      targetAudience: targetAudience ?? this.targetAudience,
      suitableForShortVideo:
          suitableForShortVideo ?? this.suitableForShortVideo,
      ceoApproved: ceoApproved ?? this.ceoApproved,
      favorite: favorite ?? this.favorite,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      "itemId": itemId,
      "title": title,
      "price": price,
      "sold": sold,
      "shopName": shopName,
      "commissionRate": commissionRate,
      "commissionAmount": commissionAmount,
      "productUrl": productUrl,
      "affiliateUrl": affiliateUrl,
      "priceBucket": priceBucket,
      "priceScore": priceScore,
      "soldBucket": soldBucket,
      "soldScore": soldScore,
      "commissionBucket": commissionBucket,
      "commissionScore": commissionScore,
      "miniBossScore": miniBossScore,
      "description": description,
      "tags": tags,
      "keywords": keywords,
      "mood": mood,
      "targetAudience": targetAudience,
      "suitableForShortVideo": suitableForShortVideo,
      "ceoApproved": ceoApproved,
      "favorite": favorite,
    };
  }

  /// ---------- Display Helpers ----------

  String get priceText => '฿$priceDisplay';

  String get soldText => 'ขาย $soldDisplay';

  String get commissionAmountText =>
      '฿${commissionAmount.toStringAsFixed(2)}';

  String get commissionRateText =>
      '${(commissionRate * 100).toStringAsFixed(0)}%';

  /// ---------- CSV Helpers ----------

  static String _read(Map<String, String> row, String key) =>
      row[key]?.trim() ?? '';

  static double _readDouble(Map<String, String> row, String key) {
    final value = _read(row, key)
        .replaceAll(',', '')
        .replaceAll('%', '');
    return double.tryParse(value) ?? 0;
  }

  static int _readInt(Map<String, String> row, String key) {
    final value = _read(row, key).replaceAll(',', '');
    return int.tryParse(value) ??
        double.tryParse(value)?.round() ??
        0;
  }

  static List<String> _split(String value) {
    if (value.trim().isEmpty) {
      return const [];
    }

    return value
        .split(',')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
  }
}