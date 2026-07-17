class Product {
  final int id;
  final String name;
  final int price;
  final int commission;
  final double rating;
  final String category;
  final String shop;
  final String? brand;
  final String? subCategory;
  final String? targetAudience;
  final bool evergreen;
  final bool giftable;

  Product({
    required this.id,
    required this.name,
    required this.price,
    required this.commission,
    required this.rating,
    required this.category,
    required this.shop,
    this.brand,
    this.subCategory,
    this.targetAudience,
    this.evergreen = false,
    this.giftable = false,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json["id"],
      name: json["name"],
      price: json["price"],
      commission: json["commission"],
      rating: (json["rating"] as num).toDouble(),
      category: json["category"],
      shop: json["shop"],
      brand: json["brand"],
      subCategory: json["subCategory"],
      targetAudience: json["targetAudience"],
      evergreen: json["evergreen"] ?? false,
      giftable: json["giftable"] ?? false,
    );
  }
}