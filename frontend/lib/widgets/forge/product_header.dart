import 'package:flutter/material.dart';

import '../../models/affiliate_product.dart';

class ProductHeader extends StatelessWidget {
  final AffiliateProduct product;

  const ProductHeader({
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
            Text(
              product.title,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 12),

            Text("🏪 ${product.shopName}"),

            const SizedBox(height: 8),

            Text("💰 ${product.priceText}"),

            Text("🛒 ${product.soldText}"),

            Text(
              "💸 ${product.commissionAmountText} (${product.commissionRateText})",
            ),
          ],
        ),
      ),
    );
  }
}