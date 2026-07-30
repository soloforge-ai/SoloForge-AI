import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

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
          content: Text("$label copied"),
          duration: const Duration(seconds: 1),
        ),
      );
    }
  }

  Future<void> _openUrl(BuildContext context, String url) async {
    if (url.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("URL not available"),
        ),
      );
      return;
    }

    final uri = Uri.parse(url);

    if (!await launchUrl(
      uri,
      mode: LaunchMode.externalApplication,
    )) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Unable to open link"),
          ),
        );
      }
    }
  }

  Widget _buildLinkSection({
    required BuildContext context,
    required String title,
    required String url,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            fontWeight: FontWeight.bold,
          ),
        ),

        const SizedBox(height: 8),

        SelectableText(
          url.isEmpty ? "-" : url,
          style: const TextStyle(
            fontSize: 12,
          ),
        ),

        const SizedBox(height: 12),

        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: url.isEmpty
                    ? null
                    : () => _copy(
                          context,
                          url,
                          title,
                        ),
                icon: const Icon(Icons.copy),
                label: const Text("Copy"),
              ),
            ),

            const SizedBox(width: 12),

            Expanded(
              child: OutlinedButton.icon(
                onPressed: url.isEmpty
                    ? null
                    : () => _openUrl(
                          context,
                          url,
                        ),
                icon: const Icon(Icons.open_in_new),
                label: const Text("Open"),
              ),
            ),
          ],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Product Assets",
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 20),

            _buildLinkSection(
              context: context,
              title: "Affiliate Link",
              url: product.affiliateUrl,
            ),

            const Divider(height: 32),

            _buildLinkSection(
              context: context,
              title: "Product Link",
              url: product.productUrl,
            ),
          ],
        ),
      ),
    );
  }
}