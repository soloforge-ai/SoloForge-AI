import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import 'prawtwan_chat_page.dart';

class DeveloperPage extends StatelessWidget {
  const DeveloperPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Developer')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Card(
            margin: EdgeInsets.zero,
            child: ListTile(
              leading: const Icon(Icons.auto_stories_outlined),
              title: const Text(
                'Test PRAWTWAN',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: const Text(
                'Open the private Pollinations fiction-editor agent and send a live test request.',
                style: TextStyle(color: AshColors.smokeSilver),
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const PrawtwanChatPage()),
                );
              },
            ),
          ),
          const SizedBox(height: 10),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 4),
            child: Text(
              'PRAWTWAN uses the existing authenticated Pollinations session. '
              'Pollen is consumed only when a message is sent.',
              style: TextStyle(
                fontSize: 11,
                height: 1.4,
                color: AshColors.smokeSilver,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
