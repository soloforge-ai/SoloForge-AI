import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import 'developer_page.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Card(
            margin: EdgeInsets.zero,
            child: ListTile(
              leading: const Icon(Icons.developer_mode_outlined),
              title: const Text(
                'Developer',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: const Text(
                'Internal tools and integration tests',
                style: TextStyle(color: AshColors.smokeSilver),
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const DeveloperPage()),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
