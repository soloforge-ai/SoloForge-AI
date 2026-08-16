import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class HeroBanner extends StatelessWidget {
  final VoidCallback? onPressed;

  const HeroBanner({super.key, this.onPressed});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: const LinearGradient(
          colors: [
            AshColors.blackPlum,
            AshColors.deepIndigo,
            AshColors.oxblood,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(color: AshColors.indigoMist, width: 0.6),
        boxShadow: const [
          BoxShadow(
            color: Color(0x33541C2A),
            blurRadius: 18,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '⚡ SoloForge AI',
                  style: TextStyle(
                    color: AshColors.boneWhite,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 4),
                Text(
                  'Build AI Products Faster',
                  style: TextStyle(
                    color: AshColors.boneWhite,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  'Discover • Analyze • Forge',
                  style: TextStyle(
                    color: AshColors.smokeSilver,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          SizedBox(
            height: 34,
            child: FilledButton.icon(
              onPressed: onPressed,
              icon: const Icon(Icons.auto_awesome, size: 16),
              label: const Text(
                'Start',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              style: FilledButton.styleFrom(
                backgroundColor: AshColors.boneWhite,
                foregroundColor: AshColors.oxblood,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
