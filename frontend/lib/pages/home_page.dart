import 'package:flutter/material.dart';

import '../models/affiliate_product.dart';
import '../services/catalog_service.dart';
import '../widgets/miniboss_dialog.dart';
import '../widgets/product_card.dart';
import '../widgets/sort_selector.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final CatalogService _catalogService = const CatalogService();

  List<AffiliateProduct> allProducts = [];
  List<AffiliateProduct> products = [];

  String keyword = '';
  SortType sortType = SortType.miniBossScore;
  bool loading = true;

  @override
  void initState() {
    super.initState();
    loadProducts();
  }

  Future<void> loadProducts() async {
    final data = await _catalogService.getProducts();

    if (!mounted) return;

    setState(() {
      allProducts = data;
      loading = false;
    });

    filterProducts();
  }

  void filterProducts() {
    final normalizedKeyword = keyword.trim().toLowerCase();
    var result = allProducts;

    if (normalizedKeyword.isNotEmpty) {
      result = result.where((product) {
        return product.title.toLowerCase().contains(normalizedKeyword) ||
            product.shopName.toLowerCase().contains(normalizedKeyword);
      }).toList();
    } else {
      result = List<AffiliateProduct>.from(result);
    }

    switch (sortType) {
      case SortType.miniBossScore:
        result.sort((a, b) => b.miniBossScore.compareTo(a.miniBossScore));
        break;
      case SortType.soldScore:
        result.sort((a, b) => b.soldScore.compareTo(a.soldScore));
        break;
      case SortType.priceScore:
        result.sort((a, b) => b.priceScore.compareTo(a.priceScore));
        break;
      case SortType.commissionScore:
        result.sort((a, b) => b.commissionScore.compareTo(a.commissionScore));
        break;
    }

    setState(() {
      products = result;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SoloForge AI'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '👔 MiniBoss Product Hunter',
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 20),
            SortSelector(
              value: sortType,
              onChanged: (value) {
                setState(() {
                  sortType = value;
                });
                filterProducts();
              },
            ),
            const SizedBox(height: 12),
            TextField(
              onChanged: (value) {
                keyword = value;
                filterProducts();
              },
              decoration: InputDecoration(
                hintText: 'Search by product title or shop name...',
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Text(
              loading
                  ? 'Loading Shopee catalog...'
                  : 'พบ ${products.length} รายการ',
              style: const TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 10),
            Expanded(
              child: loading
                  ? const Center(child: CircularProgressIndicator())
                  : ListView.builder(
                      itemCount: products.length,
                      itemBuilder: (context, index) {
                        final product = products[index];

                        return ProductCard(
                          product: product,
                          onForge: () {
                            showDialog(
                              context: context,
                              builder: (_) => MiniBossDialog(
                                product: product.toProduct(),
                              ),
                            );
                          },
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
