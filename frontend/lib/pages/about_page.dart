import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../models/version_info.dart';
import '../services/version_service.dart';
import '../widgets/version_card.dart';

class AboutPage extends StatelessWidget {
  const AboutPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('About SoloForge AI'),
      ),
      body: FutureBuilder<VersionInfo>(
        future: VersionService().loadVersion(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Text(
                'Error\n\n${snapshot.error}',
                textAlign: TextAlign.center,
              ),
            );
          }

          if (!snapshot.hasData) {
            return const Center(child: Text('No Version Information'));
          }

          final version = snapshot.data!;

          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 40),
            child: Column(
              children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF17131A),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: const Color(0xFF596989)),
                  ),
                  child: SvgPicture.asset(
                    'assets/branding/logo_master.svg',
                    width: double.infinity,
                    height: 105,
                    fit: BoxFit.contain,
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  version.appName,
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 6),
                Text(
                  'Built for Solo Creators',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 24),
                VersionCard(version: version),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Update server is not configured yet.'),
                        ),
                      );
                    },
                    icon: const Icon(Icons.system_update),
                    label: const Text('Check for Updates'),
                  ),
                ),
                const SizedBox(height: 24),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Release Notes',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          version.fullVersion,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 12),
                        const Text('• Version Center Foundation'),
                        const Text('• About Page'),
                        const Text('• Version Card'),
                        const Text('• Version Service'),
                        const Text('• Update Service'),
                        const Text('• ASH Signature Branding'),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 30),
                Text(
                  'Powered by ${version.company}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 8),
                Text(
                  '© 2026 SoloForge AI',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
