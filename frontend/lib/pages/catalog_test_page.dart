import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class CatalogTestPage extends StatefulWidget {
  const CatalogTestPage({super.key});

  @override
  State<CatalogTestPage> createState() => _CatalogTestPageState();
}

class _CatalogTestPageState extends State<CatalogTestPage> {
  bool loading = true;
  String error = '';

  List<dynamic> products = [];

  @override
  void initState() {
    super.initState();
    loadCatalog();
  }

  Future<void> loadCatalog() async {
    try {
      final jsonString =
          await rootBundle.loadString('assets/data/catalog.json');

      final data = jsonDecode(jsonString);

      setState(() {
        products = data as List<dynamic>;
        loading = false;
      });
    } catch (e) {
      setState(() {
        loading = false;
        error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (error.isNotEmpty) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Catalog Test'),
        ),
        body: Center(
          child: Text(error),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text('Catalog (${products.length})'),
      ),
      body: ListView.builder(
        itemCount: products.length,
        itemBuilder: (context, index) {
          final p = products[index];

          final images = (p['images'] as List?) ?? [];

          final image =
              images.isNotEmpty ? images.first.toString() : '';

          return Card(
            margin: const EdgeInsets.all(8),
            child: ListTile(
              leading: image.isEmpty
                  ? const Icon(Icons.image_not_supported)
                  : Image.network(
                      image,
                      width: 70,
                      fit: BoxFit.cover,
                    ),
              title: Text(
                p['title'] ?? '',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("ราคา : ฿${p['sale_price']}"),
                  Text("⭐ ${p['rating']}"),
                  Text(
                    "MiniBoss : ${p['miniboss']['grade']} (${p['miniboss']['score']})",
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}