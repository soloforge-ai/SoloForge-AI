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
      margin: const EdgeInsets.symmetric(
        horizontal: 8,
        vertical: 6,
      ),
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: SizedBox(
                width: 64,
                height: 64,
                child: product.images.isNotEmpty
                    ? Image.network(
                        product.images.first,
                        fit: BoxFit.cover,
                      )
                    : Container(
                        color: Colors.grey.shade200,
                        child: const Icon(Icons.shopping_bag),
                      ),
              ),
            ),

            const SizedBox(width: 10),

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      height: 1.25,
                    ),
                  ),

                  const SizedBox(height: 2),

                  Text(
                    product.shopName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.grey.shade600,
                    ),
                  ),

                  const SizedBox(height: 6),

                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      if (product.official)
                        _buildBadge(
                          icon: Icons.verified,
                          label: "Official",
                          color: Colors.amber,
                        ),

                      if (product.preferred)
                        _buildBadge(
                          icon: Icons.favorite,
                          label: "Preferred",
                          color: Colors.purple,
                        ),
                    ],
                  ),

                  const SizedBox(height: 6),

                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      _ScoreChip(
                        label: 'MB',
                        value: product.miniBossScore,
                        color: _scoreColor(product.miniBossScore),
                      ),

                      _ScoreChip(
                        label: 'Sold',
                        value: product.sold >= 1000
                            ? 100
                            : (product.sold / 10)
                                .clamp(0, 100)
                                .toDouble(),
                      ),

                      _ScoreChip(
                        label: 'Price',
                        value: product.price >= 1000
                            ? 100
                            : (product.price / 10).clamp(0, 100),
                      ),

                      _ScoreChip(
                        label: 'Comm',
                        value: (product.commissionAmount * 10)
                            .clamp(0, 100),
                      ),
                    ],
                  ),

                  const SizedBox(height: 8),

                  Text(
                    product.priceText,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                    ),
                  ),

                  Text(
                    product.soldText,
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey.shade600,
                    ),
                  ),

                  const SizedBox(height: 2),

                  Text(
                    'Commission ${product.commissionAmountText} (${product.commissionRateText})',
                    style: const TextStyle(
                      fontSize: 12,
                      color: Colors.deepPurple,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(width: 8),

            SizedBox(
              width: 94,
              height: 32,
              child: FilledButton(
                onPressed: onForge,
                child: const Text(
                  "🔥Forge",
                  style: TextStyle(fontSize: 12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  static Color _scoreColor(double score) {
    if (score >= 90) return Colors.green;
    if (score >= 70) return Colors.orange;
    return Colors.red;
  }
}

class _ScoreChip extends StatelessWidget {
  final String label;
  final double value;
  final Color color;

  const _ScoreChip({
    required this.label,
    required this.value,
    this.color = Colors.deepPurple,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 8,
        vertical: 4,
      ),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color),
      ),
      child: Text(
        '$label ${value.round()}',
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

Widget _buildBadge({
  required IconData icon,
  required String label,
  required Color color,
}) {
  return Container(
    padding: const EdgeInsets.symmetric(
      horizontal: 8,
      vertical: 3,
    ),
    decoration: BoxDecoration(
      color: color.withOpacity(0.12),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: color),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          icon,
          size: 12,
          color: color,
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 11,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    ),
  );
}