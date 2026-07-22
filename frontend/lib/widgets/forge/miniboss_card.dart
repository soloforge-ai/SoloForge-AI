import 'package:flutter/material.dart';

import '../../models/affiliate_product.dart';

class MiniBossCard extends StatelessWidget {
  final AffiliateProduct product;

  const MiniBossCard({
    super.key,
    required this.product,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "MiniBoss Score",
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 18,
              ),
            ),

            const SizedBox(height: 12),

            LinearProgressIndicator(
              value: product.miniBossScore / 10,
            ),

            const SizedBox(height: 12),

            Text(
              "${product.miniBossScore.toStringAsFixed(1)} / 10",
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}