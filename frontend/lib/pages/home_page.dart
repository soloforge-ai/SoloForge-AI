import 'package:flutter/material.dart';

import '../engine/miniboss_engine.dart';
import '../models/product.dart';
import '../services/product_service.dart';
import '../widgets/category_filter.dart';
import '../widgets/product_card.dart';

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

    setState(() {
      products = result;
    });
  }

  void showMiniBoss(Product product) {
  final result = MiniBossEngine.analyze(product);

  showDialog(
    context: context,
    builder: (_) => AlertDialog(
      title: Row(
        children: [
          const Icon(Icons.smart_toy),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              product.name,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            Center(
              child: Column(
                children: [
                  const Text(
                    "MiniBoss Score",
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "${result.score}/100",
                    style: const TextStyle(
                      fontSize: 30,
                      fontWeight: FontWeight.bold,
                      color: Colors.green,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            const Divider(),

            const Text(
              "Reasons",
              style: TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 8),

            ...result.reasons.map(
              (reason) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(reason),
              ),
            ),

            const Divider(),

            ListTile(
              dense: true,
              leading: const Icon(Icons.speed),
              title: const Text("Difficulty"),
              subtitle: Text(result.difficulty),
            ),

            ListTile(
              dense: true,
              leading: const Icon(Icons.groups),
              title: const Text("Competition"),
              subtitle: Text(result.competition),
            ),

            ListTile(
              dense: true,
              leading: const Icon(Icons.local_fire_department),
              title: const Text("Viral Chance"),
              subtitle: Text(result.viralChance),
            ),

            ListTile(
              dense: true,
              leading: const Icon(Icons.workspace_premium),
              title: const Text("Recommendation"),
              subtitle: Text(result.recommendation),
            ),

            ListTile(
              dense: true,
              leading: const Icon(Icons.bolt),
              title: const Text("Action"),
              subtitle: Text(result.action),
            ),
          ],
        ),
      ),
      actions: [
        FilledButton.icon(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.check),
          label: const Text("Close"),
        ),
      ],
    ),
  );
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

            const SizedBox(height: 20),

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
                  final result = MiniBossEngine.analyze(p);

                  return ProductCard(
                    product: p,
                    onForge: () => showMiniBoss(p),
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