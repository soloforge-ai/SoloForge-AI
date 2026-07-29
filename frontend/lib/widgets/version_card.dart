import 'package:flutter/material.dart';

import '../models/version_info.dart';

class VersionCard extends StatelessWidget {
  final VersionInfo version;

  const VersionCard({
    super.key,
    required this.version,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              version.appName,
              style: theme.textTheme.headlineSmall,
            ),

            const SizedBox(height: 4),

            Text(
              "Powered by ${version.company}",
              style: theme.textTheme.bodySmall,
            ),

            const Divider(height: 32),

            _infoTile(
              "Version",
              version.fullVersion,
            ),

            _infoTile(
              "Released",
              version.release,
            ),

            _infoTile(
              "MiniBoss Engine",
              version.engine,
            ),

            _infoTile(
              "Scanner",
              version.scanner,
            ),

            _infoTile(
              "API",
              version.apiVersion,
            ),

            const SizedBox(height: 24),

            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 12,
                vertical: 8,
              ),
              decoration: BoxDecoration(
                color: Colors.green.withOpacity(.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.check_circle,
                    color: Colors.green,
                    size: 18,
                  ),
                  SizedBox(width: 8),
                  Text(
                    "Latest Version",
                    style: TextStyle(
                      color: Colors.green,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoTile(
    String title,
    String value,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          Expanded(
            child: Text(value),
          ),
        ],
      ),
    );
  }
}