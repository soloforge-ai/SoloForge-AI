import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import 'developer_page.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key, this.onSignOut});

  final Future<void> Function()? onSignOut;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (onSignOut != null) ...[
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 12),
              child: Text('Account', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
            Card(
              margin: EdgeInsets.zero,
              child: ListTile(
                leading: const Icon(Icons.logout),
                title: const Text('Sign out'),
                onTap: () async {
                  Navigator.of(context).pop();
                  await onSignOut!();
                },
              ),
            ),
            const SizedBox(height: 12),
          ],
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
