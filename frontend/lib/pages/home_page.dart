import 'package:flutter/material.dart';

import '../models/affiliate_product.dart';
import '../services/catalog_service.dart';
import '../services/discovery/discovery_service.dart';

import '../widgets/product_card.dart';
import '../widgets/sort_selector.dart';
import 'forge_page.dart';
import '../widgets/category_filter_bar.dart';

import 'about_page.dart';
import '../widgets/home/hero_banner.dart';
import 'developer_tools_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final CatalogService _catalogService =
    const CatalogService();

  final DiscoveryService _discoveryService =
    const DiscoveryService();

  List<AffiliateProduct> allProducts = [];
  List<AffiliateProduct> products = [];

  String keyword = '';
  SortType sortType = SortType.miniBossScore;
  bool loading = true;

  String selectedCategory = 'All';

// TODO(Sprint45)
// จะเปลี่ยนเป็น Dynamic Category
// จาก DiscoveryService ใน Phase B

  List<String> categories = ['All'];

  @override
  void initState() {
    super.initState();

    loadCategories();
    loadProducts();
  }

  Future<void> loadCategories() async {
    final data =
        await _discoveryService.loadCategoryNames();

    if (!mounted) return;

    setState(() {
      categories = [
        'All',
        ...data,
      ];
    });
  }

  Future<void> loadProducts({
  String category = 'All',
  }) async {
    setState(() {
      loading = true;
    });

    final data =
      category == 'All'
          ? await _catalogService.getProducts()
          : await _catalogService.getCategory(
              category,
            );

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
  actions: [
    IconButton(
      tooltip: "Developer Tools",
      icon: const Icon(Icons.build),
      onPressed: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => const DeveloperToolsPage(),
          ),
        );
      },
    ),

    IconButton(
      tooltip: "About",
      icon: const Icon(Icons.info_outline),
      onPressed: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => const AboutPage(),
          ),
        );
      },
    ),
  ],
),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const HeroBanner(),
            const SizedBox(height: 16),

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
            const SizedBox(height: 12),

              if (categories.isNotEmpty)
                CategoryFilterBar(
                  categories: categories,
                  selectedCategory: selectedCategory,
                  onSelected: (category) async {
                    setState(() {
                      selectedCategory = category;
                    });

                    if (category == 'All') {
                      await loadProducts();
                    } else {
                      await loadProducts(
                        category: category,
                      );
                    }
                  },
                ),

              const SizedBox(height: 16),

              Card(
                elevation: 0,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [

                      _StatItem(
                        icon: Icons.inventory_2,
                        title: "Products",
                        value: "${products.length}",
                      ),

                      _StatItem(
                        icon: Icons.category,
                        title: "Categories",
                        value: "${categories.length - 1}",
                      ),

                      _StatItem(
                        icon: Icons.auto_awesome,
                        title: "AI Ready",
                        value: "${products.length}",
                      ),
                    ],
                  ),
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
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => ForgePage(product: product),
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
class _StatItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;

  const _StatItem({
    required this.icon,
    required this.title,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          icon,
          color: const Color(0xFF7C4DFF),
          size: 18,
        ),

        const SizedBox(height: 6),

        Text(
          value,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
          ),
        ),

        const SizedBox(height: 2),

        Text(
          title,
          style: const TextStyle(
            color: Colors.grey,
            fontSize: 12,
          ),
        ),
      ],
    );
  }
}