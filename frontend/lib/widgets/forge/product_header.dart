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
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            // --------------------------
            // Product Image
            // --------------------------

            ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Image.network(
                product.images.isNotEmpty
                    ? product.images.first
                    : '',
                width: 110,
                height: 110,
                fit: BoxFit.cover,

                loadingBuilder: (
                  context,
                  child,
                  loadingProgress,
                ) {
                  if (loadingProgress == null) {
                    return child;
                  }

                  return Container(
                    width: 110,
                    height: 110,
                    color: Colors.grey.shade900,
                    alignment: Alignment.center,
                    child: const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                      ),
                    ),
                  );
                },

                errorBuilder: (
                  context,
                  error,
                  stackTrace,
                ) {
                  return Container(
                    width: 110,
                    height: 110,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade900,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(
                      Icons.image_not_supported,
                      size: 40,
                      color: Colors.white38,
                    ),
                  );
                },
              ),
            ),

            const SizedBox(width: 18),

            // --------------------------
            // Product Info
            // --------------------------

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [

                  Text(
                    product.title,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      height: 1.25,
                    ),
                  ),

                  const SizedBox(height: 12),

                  Row(
                    children: [

                      const Icon(
                        Icons.storefront,
                        size: 18,
                        color: Colors.deepPurple,
                      ),

                      const SizedBox(width: 6),

                      Expanded(
                        child: Text(
                          product.shopName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: Colors.grey.shade400,
                          ),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 18),

                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [

                      _InfoChip(
                        Icons.sell,
                        product.priceText,
                      ),

                      _InfoChip(
                        Icons.shopping_cart,
                        product.soldText,
                      ),

                      _InfoChip(
                        Icons.paid,
                        product.commissionAmountText,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String text;

  const _InfoChip(
    this.icon,
    this.text,
  );

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 12,
        vertical: 8,
      ),
      decoration: BoxDecoration(
        color: Colors.deepPurple.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [

          Icon(
            icon,
            size: 16,
            color: Colors.deepPurple,
          ),

          const SizedBox(width: 6),

          Text(
            text,
            style: const TextStyle(
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}