import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../models/affiliate_product.dart';

class ProductAssetsCard extends StatelessWidget {
  final AffiliateProduct product;

  const ProductAssetsCard({
    super.key,
    required this.product,
  });

  Future<void> _copy(
    BuildContext context,
    String text,
    String label,
  ) async {
    await Clipboard.setData(
      ClipboardData(text: text),
    );

    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$label copied'),
          duration: const Duration(seconds: 1),
        ),
      );
    }
  }

  Widget _assetTile(
    BuildContext context, {
    required String title,
    required String value,
  }) {
    final hasValue = value.trim().isNotEmpty;

    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 12,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment:
                    CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                    ),
                  ),

                  const SizedBox(height: 6),

                  if (hasValue)
                    SizedBox(
                      width: double.infinity,
                      child: SelectableText(
                        value,
                        maxLines: 1,
                        style: TextStyle(
                          color: Colors.grey.shade500,
                          fontSize: 12,
                        ),
                      ),
                    )
                  else
                    Text(
                      "Not available",
                      style: TextStyle(
                        color: Colors.grey.shade500,
                        fontSize: 12,
                      ),
                    ),
                ],
              ),
            ),

            const SizedBox(width: 12),

            FilledButton.icon(
              onPressed: hasValue
                  ? () => _copy(
                        context,
                        value,
                        title,
                      )
                  : null,
              icon: const Icon(
                Icons.copy,
                size: 16,
              ),
              label: const Text("Copy"),
              style: FilledButton.styleFrom(
                minimumSize: const Size(
                  92,
                  40,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _assetTile(
          context,
          title: 'Affiliate Link',
          value: product.affiliateUrl,
        ),

        const SizedBox(height: 10),

        _assetTile(
          context,
          title: 'Product Link',
          value: product.productUrl,
        ),
      ],
    );
  }
}