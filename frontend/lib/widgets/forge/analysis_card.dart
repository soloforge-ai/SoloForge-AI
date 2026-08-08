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
    String value,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: Colors.deepPurpleAccent,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),

          const SizedBox(height: 4),

          Text(
            value.isEmpty ? "-" : value,
            style: const TextStyle(
              fontSize: 15,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "AI Analysis",
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 20),

            _section(
              "Category",
              intelligence.category,
            ),

            _section(
              "Keywords",
              intelligence.keywords.join(", "),
            ),

            _section(
              "Audience",
              "• ${intelligence.audience.join("\n• ")}",
            ),

            _section(
              "Selling Points",
              intelligence.sellingPoints.join("\n• "),
            ),

            _section(
              "Pain Points",
              intelligence.painPoints.join("\n• "),
            ),
          ],
        ),
      ),
    );
  }
}