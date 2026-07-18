import 'package:flutter/material.dart';

import '../engine/miniboss_engine.dart';
import '../models/product.dart';

class MiniBossDialog extends StatelessWidget {
  final Product product;

  const MiniBossDialog({
    super.key,
    required this.product,
  });

  @override
  Widget build(BuildContext context) {
    final result = MiniBossEngine.analyze(product);

    return AlertDialog(
      title: Row(
        children: [
          const Icon(Icons.smart_toy),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              product.name,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Column(
                children: [
                  const Text(
                    "MiniBoss Score",
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "${result.score}/100",
                    style: const TextStyle(
                      fontSize: 30,
                      fontWeight: FontWeight.bold,
                      color: Colors.green,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            const Divider(),

            const Text(
              "Reasons",
              style: TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 8),

            ...result.reasons.map(
              (reason) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(reason),
              ),
            ),

            const Divider(),

            ListTile(
              dense: true,
              leading: const Icon(Icons.speed),
              title: const Text("Difficulty"),
              subtitle: Text(result.difficulty),
            ),

            ListTile(
              dense: true,
              leading: const Icon(Icons.groups),
              title: const Text("Competition"),
              subtitle: Text(result.competition),
            ),

            ListTile(
              dense: true,
              leading: const Icon(Icons.local_fire_department),
              title: const Text("Viral Chance"),
              subtitle: Text(result.viralChance),
            ),

            ListTile(
              dense: true,
              leading: const Icon(Icons.workspace_premium),
              title: const Text("Recommendation"),
              subtitle: Text(result.recommendation),
            ),

            ListTile(
              dense: true,
              leading: const Icon(Icons.bolt),
              title: const Text("Action"),
              subtitle: Text(result.action),
            ),
          ],
        ),
      ),
      actions: [
        FilledButton.icon(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.check),
          label: const Text("Close"),
        ),
      ],
    );
  }
}