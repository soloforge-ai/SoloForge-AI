import 'dart:convert';

import 'package:flutter/services.dart';

import '../models/product.dart';

class ProductService {
  static Future<List<Product>> loadProducts() async {
    final jsonString =
        await rootBundle.loadString('assets/data/products.json');

    final List<dynamic> jsonData = json.decode(jsonString);

    return jsonData
        .map((item) => Product.fromJson(item))
        .toList();
  }
}