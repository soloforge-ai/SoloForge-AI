import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import '../models/affiliate_product.dart';
import '../services/catalog_service.dart';
import '../services/discovery/discovery_service.dart';
import '../widgets/category_filter_bar.dart';
import '../widgets/home/hero_banner.dart';
import '../widgets/sort_selector.dart';
import 'about_page.dart';
import 'developer_tools_page.dart';
import 'forge_page.dart';
import 'sticker_forge_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final CatalogService _catalogService = const CatalogService();
  final DiscoveryService _discoveryService = const DiscoveryService();

  List<AffiliateProduct> allProducts = [];
  List<AffiliateProduct> products = [];

  String keyword = '';
  SortType sortType = SortType.miniBossScore;
  bool loading = true;
  String selectedCategory = 'All';
  List<String> categories = ['All'];

  @override
  void initState() {
    super.initState();
    loadCategories();
    loadProducts();
  }

  Future<void> loadCategories() async {
    final data = await _discoveryService.loadCategoryNames();
    if (!mounted) return;
    setState(() => categories = ['All', ...data]);
  }

  Future<void> loadProducts({String category = 'All'}) async {
    setState(() => loading = true);
    final data = category == 'All'
        ? await _catalogService.getProducts()
        : await _catalogService.getCategory(category);
    if (!mounted) return;
    allProducts = data;
    loading = false;
    filterProducts();
  }

  void filterProducts() {
    final normalizedKeyword = keyword.trim().toLowerCase();
    var result = List<AffiliateProduct>.from(allProducts);

    if (normalizedKeyword.isNotEmpty) {
      result = result.where((product) {
        return product.title.toLowerCase().contains(normalizedKeyword) ||
            product.shopName.toLowerCase().contains(normalizedKeyword);
      }).toList();
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

    if (!mounted) return;
    setState(() => products = result);
  }

  void openStickerForge() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const StickerForgePage()),
    );
  }

  void openProductForge(AffiliateProduct product) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => ForgePage(product: product)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SoloForge AI'),
        actions: [
          IconButton(
            tooltip: 'Developer Tools',
            icon: const Icon(Icons.build),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const DeveloperToolsPage()),
              );
            },
          ),
          IconButton(
            tooltip: 'About',
            icon: const Icon(Icons.info_outline),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const AboutPage()),
              );
            },
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.fromLTRB(12, 4, 12, 0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            HeroBanner(onPressed: openStickerForge),
            const SizedBox(height: 5),
            SizedBox(
              height: 38,
              child: Row(
                children: [
                  Expanded(
                    child: SortSelector(
                      value: sortType,
                      onChanged: (value) {
                        setState(() => sortType = value);
                        filterProducts();
                      },
                    ),
                  ),
                  const SizedBox(width: 6),
                  Container(
                    height: 38,
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    decoration: BoxDecoration(
                      color: AshColors.blackPlum,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: AshColors.indigoMist.withValues(alpha: 0.7),
                      ),
                    ),
                    child: Center(
                      child: Text(
                        '${products.length}',
                        style: const TextStyle(
                          color: AshColors.boneWhite,
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 5),
            SizedBox(
              height: 42,
              child: TextField(
                onChanged: (value) {
                  keyword = value;
                  filterProducts();
                },
                decoration: InputDecoration(
                  hintText: 'Search product or shop...',
                  prefixIcon: const Icon(Icons.search, size: 19),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 10),
                ),
              ),
            ),
            const SizedBox(height: 4),
            if (categories.isNotEmpty)
              SizedBox(
                height: 36,
                child: CategoryFilterBar(
                  categories: categories,
                  selectedCategory: selectedCategory,
                  onSelected: (category) async {
                    setState(() => selectedCategory = category);
                    await loadProducts(category: category);
                  },
                ),
              ),
            const SizedBox(height: 3),
            Row(
              children: [
                const Icon(
                  Icons.inventory_2_outlined,
                  size: 15,
                  color: AshColors.indigoMist,
                ),
                const SizedBox(width: 5),
                const Text(
                  'Products',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    color: AshColors.boneWhite,
                  ),
                ),
                const Spacer(),
                Text(
                  '${products.length} • MiniBoss priority',
                  style: const TextStyle(
                    fontSize: 9,
                    color: AshColors.smokeSilver,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 2),
            Expanded(
              child: loading
                  ? const Center(child: CircularProgressIndicator())
                  : products.isEmpty
                      ? const Center(child: Text('No products found.'))
                      : LayoutBuilder(
                          builder: (context, constraints) {
                            final columns = constraints.maxWidth >= 720 ? 3 : 2;
                            return GridView.builder(
                              padding: const EdgeInsets.only(bottom: 12),
                              gridDelegate:
                                  SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: columns,
                                crossAxisSpacing: 7,
                                mainAxisSpacing: 7,
                                childAspectRatio: columns == 2 ? 0.86 : 0.90,
                              ),
                              itemCount: products.length,
                              itemBuilder: (context, index) {
                                final product = products[index];
                                return _CompactProductCard(
                                  product: product,
                                  onForge: () => openProductForge(product),
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

class _CompactProductCard extends StatelessWidget {
  final AffiliateProduct product;
  final VoidCallback onForge;

  const _CompactProductCard({
    required this.product,
    required this.onForge,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onForge,
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 7,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: SizedBox(
                    width: double.infinity,
                    child: product.images.isNotEmpty
                        ? Image.network(
                            product.images.first,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => const _ImageFallback(),
                          )
                        : const _ImageFallback(),
                  ),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                product.title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 11,
                  height: 1.08,
                  fontWeight: FontWeight.w800,
                  color: AshColors.boneWhite,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                product.shopName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 9,
                  color: AshColors.smokeSilver,
                ),
              ),
              const SizedBox(height: 3),
              Row(
                children: [
                  const Icon(Icons.star_rounded, size: 12, color: AshColors.indigoMist),
                  const SizedBox(width: 2),
                  Text(
                    product.miniBossScore.toStringAsFixed(0),
                    style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700),
                  ),
                  const Spacer(),
                  Text(
                    product.priceText,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w900,
                      color: AshColors.boneWhite,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              SizedBox(
                width: double.infinity,
                height: 27,
                child: FilledButton.icon(
                  onPressed: onForge,
                  icon: const Icon(Icons.auto_awesome, size: 12),
                  label: const Text('SoloForge AI', style: TextStyle(fontSize: 10)),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ImageFallback extends StatelessWidget {
  const _ImageFallback();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AshColors.blackPlum,
      alignment: Alignment.center,
      child: const Icon(
        Icons.image_not_supported_outlined,
        color: AshColors.smokeSilver,
        size: 26,
      ),
    );
  }
}
