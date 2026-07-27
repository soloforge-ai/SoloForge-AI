import 'dart:convert';

import 'package:flutter/services.dart';

class JsonlCatalogService {
  const JsonlCatalogService();

  /// Load a single JSONL chunk
  Future<List<Map<String, dynamic>>> loadChunk({
    required String chunkFile,
  }) async {
    try {
      final jsonl = await rootBundle.loadString(
        'assets/data/processed/$chunkFile',
      );

      final lines = jsonl.split('\n').where((line) => line.trim().isNotEmpty);

      return lines
          .map((line) => jsonDecode(line) as Map<String, dynamic>)
          .toList();
    } catch (e) {
      print('Failed to load $chunkFile');
      print(e);
      return [];
    }
  }

  /// Load multiple chunks
  Future<List<Map<String, dynamic>>> loadAllChunks(
    List<String> chunkFiles,
  ) async {
    final products = <Map<String, dynamic>>[];

    for (final chunk in chunkFiles) {
      final data = await loadChunk(chunkFile: chunk);
      products.addAll(data);
    }

    return products;
  }

  /// Load first N products from chunks
  Future<List<Map<String, dynamic>>> loadTopProducts({
    required List<String> chunkFiles,
    int limit = 1000,
  }) async {
    final products = <Map<String, dynamic>>[];

    for (final chunk in chunkFiles) {
      final data = await loadChunk(chunkFile: chunk);

      products.addAll(data);

      if (products.length >= limit) {
        return products.take(limit).toList();
      }
    }

    return products;
  }
}
