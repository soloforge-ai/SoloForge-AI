import 'dart:convert';

import 'package:flutter/services.dart';

import '../datasources/abstract/affiliate_data_source.dart';
import '../models/affiliate_product.dart';
import 'product_search_service.dart';

class CatalogService implements AffiliateDataSource {
  const CatalogService({this.assetPath = 'assets/data/catalog.json'});

  final String assetPath;

  @override
  Future<List<AffiliateProduct>> getProducts() async {
    final jsonString = await rootBundle.loadString(assetPath);

    final List<dynamic> data = jsonDecode(jsonString) as List<dynamic>;

    final products = data
        .map((e) => AffiliateProduct.fromJson(e as Map<String, dynamic>))
        .toList();

    products.sort((a, b) => b.miniBossScore.compareTo(a.miniBossScore));

    return products;
  }

  @override
  Future<List<AffiliateProduct>> search(String keyword) async {
    final products = await getProducts();

    return const ProductSearchService().search(products, keyword);
  }
}
