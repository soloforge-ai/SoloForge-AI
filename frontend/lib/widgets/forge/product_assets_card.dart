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
    await Clipboard.setData(ClipboardData(text: text));

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
    return Card(
      elevation: 0,
      color: Colors.grey.shade600,
      child: Padding(
        padding: const EdgeInsets.all(13),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 1),
            SelectableText(
              value,
              style: const TextStyle(fontSize: 15),
            ),
            const SizedBox(height: 1),
            Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton.icon(
                onPressed: () => _copy(context, value, title),
                icon: const Icon(Icons.copy, size: 12),
                label: const Text('Copy'),
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