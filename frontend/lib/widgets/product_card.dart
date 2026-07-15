import 'package:flutter/material.dart';

import '../engine/miniboss_engine.dart';
import '../models/product.dart';

class ProductCard extends StatelessWidget {
  final Product product;
  final VoidCallback onForge;

  const ProductCard({
    super.key,
    required this.product,
    required this.onForge,
  });

  @override
  Widget build(BuildContext context) {
    final result = MiniBossEngine.analyze(product);

    return Card(
      child: ListTile(
        leading: const CircleAvatar(
          radius: 24,
          backgroundColor: Colors.deepPurple,
          child: Icon(
            Icons.shopping_bag,
            color: Colors.white,
          ),
        ),

        title: Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Text(
            product.name,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 20,
            ),
          ),
        ),

        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            Row(
              children: [

                Text(
                  "MiniBoss Score : ${result.score}/100",
                  style: TextStyle(
                    color: result.score >= 90
                        ? Colors.green
                        : result.score >= 75
                            ? Colors.orange
                            : Colors.red,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),

                const SizedBox(width: 8),

                Icon(
                  Icons.auto_awesome,
                  size: 18,
                  color: result.score >= 90
                      ? Colors.green
                      : result.score >= 75
                          ? Colors.orange
                          : Colors.red,
                ),
              ],
            ),

            const SizedBox(height: 8),

            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: result.reasons.map((reason) {
                return Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.deepPurple.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    reason,
                    style: const TextStyle(
                      fontSize: 11,
                    ),
                  ),
                );
              }).toList(),
            ),

            const SizedBox(height: 8),

            Text(
              "฿${product.price}   ⭐ ${product.rating}",
            ),
          ],
        ),

        trailing: FilledButton(
          onPressed: onForge,
          child: const Text("Forge"),
        ),
      ),
    );
  }
}