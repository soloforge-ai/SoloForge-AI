import 'package:flutter/material.dart';

import '../models/affiliate_product.dart';

import 'badge.dart';
import 'forge_button.dart';
import 'score_chip.dart';

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
        horizontal: 12,
        vertical: 4,
      ),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            // -------------------------------------------------
            // Product Image
            // -------------------------------------------------

            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: SizedBox(
                width: 84,
                height: 84,
                child: product.images.isNotEmpty
                    ? Image.network(
                        product.images.first,
                        fit: BoxFit.cover,
                        errorBuilder: (
                          context,
                          error,
                          stackTrace,
                        ) {
                          return Container(
                            color: Colors.grey.shade300,
                            child: const Icon(
                              Icons.image_not_supported,
                              size: 32,
                            ),
                          );
                        },
                      )
                    : Container(
                        color: Colors.grey.shade300,
                        child: const Icon(
                          Icons.shopping_bag,
                          size: 32,
                        ),
                      ),
              ),
            ),

            const SizedBox(width: 12),

            // -------------------------------------------------
            // Product Detail
            // -------------------------------------------------

            Expanded(
              child: Column(
                crossAxisAlignment:
                    CrossAxisAlignment.start,
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

                  const SizedBox(height: 4),

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
                    spacing: 4,
                    runSpacing: 4,
                    children: [

                      if (product.official)
                        ProductBadge(
                          icon: Icons.verified,
                          label: "Official",
                          color: Colors.amber,
                        ),

                      if (product.preferred)
                        ProductBadge(
                          icon: Icons.favorite,
                          label: "Preferred",
                          color: Colors.purple,
                        ),
                    ],
                  ),

                  const SizedBox(height: 6),

                  Wrap(
                    spacing: 4,
                    runSpacing: 4,
                    children: [

                      ScoreChip(
                        label: "MB",
                        value: product.miniBossScore,
                        color: _scoreColor(
                          product.miniBossScore,
                        ),
                      ),

                      ScoreChip(
                        label: "Sold",
                        value: product.sold >= 1000
                            ? 100
                            : (product.sold / 10)
                                .clamp(0, 100)
                                .toDouble(),
                      ),

                      ScoreChip(
                        label: "Price",
                        value: product.price >= 1000
                            ? 100
                            : (product.price / 10)
                                .clamp(0, 100),
                      ),

                      ScoreChip(
                        label: "Comm",
                        value: (product
                                .commissionAmount *
                            10)
                            .clamp(0, 100),
                      ),
                    ],
                  ),

                  const SizedBox(height: 8),

                  Row(
                    children: [

                      Expanded(
                        child: Column(
                          crossAxisAlignment:
                              CrossAxisAlignment.start,
                          children: [

                            Text(
                              product.priceText,
                              style:
                                  const TextStyle(
                                fontSize: 15,
                                fontWeight:
                                    FontWeight.bold,
                              ),
                            ),

                            Text(
                              product.soldText,
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors
                                    .grey.shade600,
                              ),
                            ),

                            Text(
                              "Commission ${product.commissionAmountText} (${product.commissionRateText})",
                              style:
                                  const TextStyle(
                                fontSize: 12,
                                color:
                                    Colors.deepPurple,
                                fontWeight:
                                    FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),

                      ForgeButton(
                        onPressed: onForge,
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

    static Color _scoreColor(double score) {
    if (score >= 90) {
      return Colors.green;
    }

    if (score >= 70) {
      return Colors.orange;
    }

    return Colors.red;
  }
}