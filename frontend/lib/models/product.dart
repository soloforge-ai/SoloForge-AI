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

  Product copyWith({
    int? id,
    String? name,
    int? price,
    int? commission,
    double? rating,
    String? category,
    String? shop,
    String? brand,
    String? subCategory,
    String? targetAudience,
    bool? evergreen,
    bool? giftable,
    String? description,
    List<String>? tags,
    List<String>? keywords,
    String? mood,
    bool? suitableForShortVideo,
    bool? ceoApproved,
  }) {
    return Product(
      id: id ?? this.id,
      name: name ?? this.name,
      price: price ?? this.price,
      commission: commission ?? this.commission,
      rating: rating ?? this.rating,
      category: category ?? this.category,
      shop: shop ?? this.shop,
      brand: brand ?? this.brand,
      subCategory: subCategory ?? this.subCategory,
      targetAudience: targetAudience ?? this.targetAudience,
      evergreen: evergreen ?? this.evergreen,
      giftable: giftable ?? this.giftable,
      description: description ?? this.description,
      tags: tags ?? this.tags,
      keywords: keywords ?? this.keywords,
      mood: mood ?? this.mood,
      suitableForShortVideo:
          suitableForShortVideo ?? this.suitableForShortVideo,
      ceoApproved: ceoApproved ?? this.ceoApproved,
    );
  }

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