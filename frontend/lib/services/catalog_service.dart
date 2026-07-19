import 'package:csv/csv.dart';
import 'package:flutter/services.dart';

import '../datasources/abstract/affiliate_data_source.dart';
import '../models/affiliate_product.dart';

/// Loads and queries the Shopee master affiliate catalog CSV asset.
class CatalogService implements AffiliateDataSource {
  const CatalogService({
    this.assetPath = 'assets/data/Shopee_MasterCatalog.csv',
    CsvDecoder csvDecoder = const CsvDecoder(),
  }) : _csvDecoder = csvDecoder;

  final String assetPath;
  final CsvDecoder _csvDecoder;

  @override
  Future<List<AffiliateProduct>> getProducts() async {
    final csv = await rootBundle.loadString(assetPath);
    final rows = _csvDecoder.convert(csv);

    if (rows.isEmpty) {
      return [];
    }

    final headers = rows.first.map((header) => header.toString().trim()).toList();
    final products = rows.skip(1).where(_hasValues).map((row) {
      final values = <String, String>{};

      for (var index = 0; index < headers.length; index++) {
        values[headers[index]] = index < row.length ? row[index].toString() : '';
      }

      return AffiliateProduct.fromCsv(values);
    }).toList();

    return products..sort(_compareByMiniBossScoreDescending);
  }

  @override
  Future<List<AffiliateProduct>> search(String keyword) async {
    final normalizedKeyword = keyword.trim().toLowerCase();
    final products = await getProducts();

    if (normalizedKeyword.isEmpty) {
      return products;
    }

    return products.where((product) {
      return product.title.toLowerCase().contains(normalizedKeyword) ||
          product.shopName.toLowerCase().contains(normalizedKeyword);
    }).toList();
  }

  static bool _hasValues(List<dynamic> row) {
    return row.any((value) => value.toString().trim().isNotEmpty);
  }

  static int _compareByMiniBossScoreDescending(
    AffiliateProduct first,
    AffiliateProduct second,
  ) {
    return second.miniBossScore.compareTo(first.miniBossScore);
  }
}
