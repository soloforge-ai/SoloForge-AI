import 'package:flutter/material.dart';

import '../../ai/product_intelligence.dart';

class AnalysisCard extends StatelessWidget {
  final ProductIntelligence intelligence;

  const AnalysisCard({
    super.key,
    required this.intelligence,
  });

  Widget _section(
    String title,
    List<String> items,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 4),
        ...items.map(
          (e) => Text("• $e"),
        ),
        const SizedBox(height: 12),
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
              "AI Analysis",
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 16),

            Text(
              "Category : ${intelligence.category}",
              style: const TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 16),

            _section(
              "Keywords",
              intelligence.keywords,
            ),

            _section(
              "Audience",
              intelligence.audience,
            ),

            _section(
              "Selling Points",
              intelligence.sellingPoints,
            ),

            _section(
              "Pain Points",
              intelligence.painPoints,
            ),
          ],
        ),
      ),
    );
  }
}