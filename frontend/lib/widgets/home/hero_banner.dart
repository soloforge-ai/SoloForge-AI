import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class HeroBanner extends StatelessWidget {
  final VoidCallback? onPressed;

  const HeroBanner({super.key, this.onPressed});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
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
            blurRadius: 16,
            offset: Offset(0, 6),
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
                    fontSize: 19,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 3),
                Text(
                  'Build AI Products Faster',
                  style: TextStyle(
                    color: AshColors.boneWhite,
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  'Discover • Analyze • Forge',
                  style: TextStyle(
                    color: AshColors.smokeSilver,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            height: 36,
            child: FilledButton.icon(
              onPressed: onPressed,
              icon: const Icon(Icons.emoji_emotions_outlined, size: 16),
              label: const Text(
                'สร้างสติ๊กเกอร์',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
              ),
              style: FilledButton.styleFrom(
                backgroundColor: AshColors.boneWhite,
                foregroundColor: AshColors.oxblood,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(22),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
