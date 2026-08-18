import 'package:flutter/material.dart';

import '../model_intelligence/pages/model_intelligence_page.dart';
import 'image_test_page.dart';

class DeveloperToolsPage extends StatelessWidget {
  const DeveloperToolsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Developer Tools'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            child: ListTile(
              leading: const Icon(Icons.auto_awesome),
              title: const Text('Model Intelligence'),
              subtitle: const Text(
                'Inspect live AI models, modalities, and capabilities',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const ModelIntelligencePage(),
                  ),
                );
              },
            ),
          ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.image),
              title: const Text('Image Engine Test'),
              subtitle: const Text(
                'Test AI Image Prompt Engine',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const ImageTestPage(),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
