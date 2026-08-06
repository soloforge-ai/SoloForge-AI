import 'dart:convert';

import 'package:flutter/services.dart';
import '../../models/affiliate_product.dart';

class DiscoveryService {
  const DiscoveryService();

  static const String _basePath = 'assets/data';

  /// ------------------------------------------------------------
  /// Load category_index.json
  /// ------------------------------------------------------------

  Future<Map<String, dynamic>> loadCategoryIndex() async {
    final jsonString = await rootBundle.loadString(
      '$_basePath/category_index.json',
    );

    return json.decode(jsonString) as Map<String, dynamic>;
  }

  /// ------------------------------------------------------------
  /// Load discovery_report.json
  /// ------------------------------------------------------------

  Future<Map<String, dynamic>> loadDiscoveryReport() async {
    final jsonString = await rootBundle.loadString(
      '$_basePath/discovery_report.json',
    );

    return json.decode(jsonString) as Map<String, dynamic>;
  }

  /// ------------------------------------------------------------
  /// Load Chunk File
  /// Example:
  /// categories/Beauty/chunk_0001.json
  /// ------------------------------------------------------------

  Future<List<Map<String, dynamic>>> loadChunk(
    String chunkFile,
  ) async {
    final jsonString = await rootBundle.loadString(
      '$_basePath/$chunkFile',
    );

    final Map<String, dynamic> jsonData =
        json.decode(jsonString);

    return (jsonData['products'] as List)
        .cast<Map<String, dynamic>>();
  }
  
  /// ------------------------------------------------------------
  /// Load Products by Category Name
  /// Example:
  /// Beauty
  /// Home & Living
  /// ------------------------------------------------------------

  Future<List<AffiliateProduct>> loadProducts(
    String categoryName,
  ) async {
    final index = await loadCategoryIndex();

    if (!index.containsKey(categoryName)) {
      return [];
    }

    final List<dynamic> chunks =
        index[categoryName]['chunks'];

    final List<AffiliateProduct> products = [];

    for (final chunk in chunks) {
      final data = await loadChunk(
        chunk as String,
      );

      products.addAll(
        data.map(
          (e) => AffiliateProduct.fromJson(e),
        ),
      );
    }

    return products;
  }

  /// ------------------------------------------------------------
  /// Category Names
  /// ------------------------------------------------------------

  Future<List<String>> loadCategoryNames() async {
    final index = await loadCategoryIndex();

    return index.keys.toList()..sort();
  }

  /// ------------------------------------------------------------
  /// Category Summary
  /// ------------------------------------------------------------

  Future<List<Map<String, dynamic>>> loadCategories() async {
    final index = await loadCategoryIndex();

    return index.values
        .cast<Map<String, dynamic>>()
        .toList();
  }

  /// ------------------------------------------------------------
  /// Featured Products
  ///
  /// Load Top N products from every category
  /// ------------------------------------------------------------

Future<List<AffiliateProduct>> loadFeaturedProducts({
  int limitPerCategory = 20,
}) async {
  final index = await loadCategoryIndex();

  final List<AffiliateProduct> result = [];

  for (final value in index.values) {
    final List<dynamic> chunks =
        value['chunks'];

    if (chunks.isEmpty) {
      continue;
    }

    final products = await loadChunk(
      chunks.first as String,
    );

    result.addAll(
      products
          .take(limitPerCategory)
          .map(
            (e) => AffiliateProduct.fromJson(e),
          ),
    );
  }

  result.sort(
    (a, b) =>
        b.miniBossScore.compareTo(
          a.miniBossScore,
        ),
  );

  return result;
}
}