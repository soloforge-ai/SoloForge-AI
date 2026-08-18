import 'package:flutter/material.dart';

import '../models/affiliate_product.dart';
import '../models/forge_result.dart';
import '../services/ai_forge_service.dart';

class AIForgePage extends StatefulWidget {
  final AffiliateProduct product;

  const AIForgePage({super.key, required this.product});

  @override
  State<AIForgePage> createState() => _AIForgePageState();
}

class _AIForgePageState extends State<AIForgePage> {
  final AIForgeService _forgeService = const AIForgeService();

  ForgeResult? _result;

  void _generate() {
    setState(() {
      _result = _forgeService.forge(widget.product);
    });
  }

  Widget _buildSection({required String title, required String text}) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
            ),
            const SizedBox(height: 10),
            SelectableText(text),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final product = widget.product;

    return Scaffold(
      appBar: AppBar(title: const Text("SoloForge AI")),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            Text(
              product.title,
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),

            const SizedBox(height: 8),

            Text("ราคา ${product.priceText}"),

            Text("MiniBoss ${product.miniBossScore.toStringAsFixed(1)}"),

            const SizedBox(height: 20),

            ElevatedButton.icon(
              onPressed: _generate,
              icon: const Icon(Icons.auto_awesome),
              label: const Text("Forge Content"),
            ),

            const SizedBox(height: 24),

            if (_result != null) ...[
              _buildSection(title: "🔥 Hook", text: _result!.hook),

              _buildSection(title: "📝 Caption", text: _result!.caption),

              _buildSection(title: "📣 CTA", text: _result!.cta),

              _buildSection(title: "🎬 Script", text: _result!.script),
            ],
          ],
        ),
      ),
    );
  }
}
