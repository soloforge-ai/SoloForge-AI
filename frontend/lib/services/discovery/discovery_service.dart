import 'dart:convert';

import 'package:flutter/services.dart';

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
    String fileName,
  ) async {
    final jsonString = await rootBundle.loadString(
      '$_basePath/$fileName',
    );

    final Map<String, dynamic> jsonData =
        json.decode(jsonString);

    final List<dynamic> products =
        jsonData['products'] ?? [];

    return products.cast<Map<String, dynamic>>();
  }

  /// ------------------------------------------------------------
  /// Load Products by Category
  ///
  /// Merge every chunk into one List
  /// ------------------------------------------------------------

  Future<List<Map<String, dynamic>>> loadProducts(
    String categoryName,
  ) async {
    final index = await loadCategoryIndex();

    if (!index.containsKey(categoryName)) {
      return [];
    }

    final List<dynamic> chunks =
        index[categoryName]['chunks'];

    final List<Map<String, dynamic>> products = [];

    for (final chunk in chunks) {
      final data = await loadChunk(
        chunk as String,
      );

      products.addAll(data);
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
  /// Load only first chunk from every category
  /// ------------------------------------------------------------

  Future<List<Map<String, dynamic>>> loadFeaturedProducts({
    int limitPerCategory = 20,
  }) async {
    final index = await loadCategoryIndex();

    final List<Map<String, dynamic>> result = [];

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
        products.take(limitPerCategory),
      );
    }

    result.sort((a, b) {
      final scoreA =
          ((a['miniBossScore'] ?? 0) as num)
              .toDouble();

      final scoreB =
          ((b['miniBossScore'] ?? 0) as num)
              .toDouble();

      return scoreB.compareTo(scoreA);
    });

    return result;
  }
}