class AffiliateProduct {
  final String id;
  final String title;
  final String brand;
  final String category;

  final double price;
  final double salePrice;
  final double rating;

  final int sold;
  final int stock;

  final List<String> images;

  final String productUrl;
  final String shortUrl;

  final String shopName;
  final double shopRating;

  final bool officialShop;
  final bool preferredShop;

  final double minibossScore;
  final String minibossGrade;

  final List<String> reasons;

  const AffiliateProduct({
    required this.id,
    required this.title,
    required this.brand,
    required this.category,
    required this.price,
    required this.salePrice,
    required this.rating,
    required this.sold,
    required this.stock,
    required this.images,
    required this.productUrl,
    required this.shortUrl,
    required this.shopName,
    required this.shopRating,
    required this.officialShop,
    required this.preferredShop,
    required this.minibossScore,
    required this.minibossGrade,
    required this.reasons,
  });

  factory AffiliateProduct.fromJson(Map<String, dynamic> json) {
    return AffiliateProduct(
      id: json['id']?.toString() ?? '',
      title: json['title'] ?? '',
      brand: json['brand'] ?? '',
      category: json['category'] ?? '',

      price: (json['price'] ?? 0).toDouble(),
      salePrice: (json['sale_price'] ?? 0).toDouble(),
      rating: (json['rating'] ?? 0).toDouble(),

      sold: json['sold'] ?? 0,
      stock: json['stock'] ?? 0,

      images: List<String>.from(json['images'] ?? []),

      productUrl: json['links']?['product'] ?? '',
      shortUrl: json['links']?['short'] ?? '',

      shopName: json['shop']?['name'] ?? '',
      shopRating: (json['shop']?['rating'] ?? 0).toDouble(),

      officialShop: json['shop']?['official'] ?? false,
      preferredShop: json['shop']?['preferred'] ?? false,

      minibossScore: (json['miniboss']?['score'] ?? 0).toDouble(),

      minibossGrade: json['miniboss']?['grade'] ?? '',

      reasons: List<String>.from(json['miniboss']?['reasons'] ?? []),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'brand': brand,
      'category': category,
      'price': price,
      'sale_price': salePrice,
      'rating': rating,
      'sold': sold,
      'stock': stock,
      'images': images,
      'productUrl': productUrl,
      'shortUrl': shortUrl,
      'shopName': shopName,
      'shopRating': shopRating,
      'officialShop': officialShop,
      'preferredShop': preferredShop,
      'minibossScore': minibossScore,
      'minibossGrade': minibossGrade,
      'reasons': reasons,
    };
  }
}
