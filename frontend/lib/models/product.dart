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

  // ==========================
  // SoloForge Metadata
  // ==========================

  final String? description;

  final List<String> tags;

  final List<String> keywords;

  final String? mood;

  final bool suitableForShortVideo;

  final bool ceoApproved;

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

    // Metadata
    this.description,
    this.tags = const [],
    this.keywords = const [],
    this.mood,
    this.suitableForShortVideo = false,
    this.ceoApproved = false,
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

      // Metadata
      description: json["description"],

      tags: List<String>.from(json["tags"] ?? const []),

      keywords: List<String>.from(json["keywords"] ?? const []),

      mood: json["mood"],

      suitableForShortVideo:
          json["suitableForShortVideo"] ?? false,

      ceoApproved:
          json["ceoApproved"] ?? false,
    );
  }

Map<String, dynamic> toJson() {
  return {
    "id": id,
    "name": name,
    "price": price,
    "commission": commission,
    "rating": rating,
    "category": category,
    "shop": shop,
    "brand": brand,
    "subCategory": subCategory,
    "targetAudience": targetAudience,
    "evergreen": evergreen,
    "giftable": giftable,
    "description": description,
    "tags": tags,
    "keywords": keywords,
    "mood": mood,
    "suitableForShortVideo": suitableForShortVideo,
    "ceoApproved": ceoApproved,
  };
}
}