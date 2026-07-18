import 'package:flutter/material.dart';

import '../engine/miniboss_engine.dart';
import '../models/product.dart';
import '../services/product_service.dart';
import '../widgets/category_filter.dart';
import '../widgets/product_card.dart';
import '../widgets/sort_selector.dart';
import '../widgets/miniboss_dialog.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  List<Product> allProducts = [];
  List<Product> products = [];

  String selectedCategory = "All";
  String keyword = "";
  SortType sortType = SortType.score;

  @override
  void initState() {
    super.initState();
    loadProducts();
  }

  Future<void> loadProducts() async {
    final data = await ProductService.loadProducts();

data.sort((a, b) {
  final scoreA = MiniBossEngine.analyze(a).score;
  final scoreB = MiniBossEngine.analyze(b).score;
  return scoreB.compareTo(scoreA);
});

setState(() {
  allProducts = data;
  filterProducts();
});
  }

  void filterProducts() {
    List<Product> result = allProducts;

    if (selectedCategory != "All") {
      result = result.where((p) => p.category == selectedCategory).toList();
    }

    if (keyword.isNotEmpty) {
      result = result.where((p) {
        return p.name.toLowerCase().contains(keyword.toLowerCase());
      }).toList();
    }

    switch (sortType) {
  case SortType.score:
    result.sort((a, b) =>
        MiniBossEngine.analyze(b).score.compareTo(
              MiniBossEngine.analyze(a).score,
            ));
    break;

  case SortType.commission:
    result.sort((a, b) => b.commission.compareTo(a.commission));
    break;

  case SortType.rating:
    result.sort((a, b) => b.rating.compareTo(a.rating));
    break;

  case SortType.price:
    result.sort((a, b) => a.price.compareTo(b.price));
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
        title: const Text("SoloForge AI"),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "👔 MiniBoss Product Hunter",
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 20),

            CategoryFilter(
              selected: selectedCategory,
              onSelected: (value) {
                setState(() {
                  selectedCategory = value;
                });
                filterProducts();
              },
            ),

            const SizedBox(height: 12),

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
                hintText: "ค้นหาสินค้า...",
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),

            const SizedBox(height: 20),

            Text(
              "พบ ${products.length} รายการ",
              style: const TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 10),

            Expanded(
              child: ListView.builder(
                itemCount: products.length,
                itemBuilder: (context, index) {
                  final p = products[index];

                  return ProductCard(
                    product: p,
                    onForge: () {
  showDialog(
    context: context,
    builder: (_) => MiniBossDialog(
      product: p,
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