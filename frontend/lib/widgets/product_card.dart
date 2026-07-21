import 'package:flutter/material.dart';

import '../models/affiliate_product.dart';

class ProductCard extends StatelessWidget {
  final AffiliateProduct product;
  final VoidCallback onForge;

  const ProductCard({
    super.key,
    required this.product,
    required this.onForge,
  });

  @override
  Widget build(BuildContext context) {
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
            product.title,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 20,
            ),
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              product.shopName,
              style: const TextStyle(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _ScoreChip(
                  label: 'MiniBoss',
                  value: product.miniBossScore,
                  color: _scoreColor(product.miniBossScore),
                ),
                _ScoreChip(
                  label: 'Sold',
                  value: product.soldScore,
                ),
                _ScoreChip(
                  label: 'Price',
                  value: product.priceScore,
                ),
                _ScoreChip(
                  label: 'Commission',
                  value: product.commissionScore,
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Product Information
            Text(
              '${product.priceText}   ${product.soldText}',
              style: const TextStyle(
                fontWeight: FontWeight.w600,
              ),
            ),

            const SizedBox(height: 4),

            Text(
              'Commission ${product.commissionAmountText} (${product.commissionRateText})',
              style: const TextStyle(
                color: Colors.deepPurple,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        trailing: FilledButton(
          onPressed: onForge,
          child: const Text('Forge'),
        ),
      ),
    );
  }

  static Color _scoreColor(double score) {
    if (score >= 4.5) return Colors.green;
    if (score >= 2.5) return Colors.orange;
    return Colors.red;
  }
}

class _ScoreChip extends StatelessWidget {
  const _ScoreChip({
    required this.label,
    required this.value,
    this.color = Colors.deepPurple,
  });

  final String label;
  final double value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 8,
        vertical: 4,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        '$label: ${value.toStringAsFixed(0)}',
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}