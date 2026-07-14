class Product {
  final int id;
  final String name;
  final int price;
  final int commission;
  final double rating;
  final String category;
  final String shop;

  Product({
    required this.id,
    required this.name,
    required this.price,
    required this.commission,
    required this.rating,
    required this.category,
    required this.shop,
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
    );
  }
}