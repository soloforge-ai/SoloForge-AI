import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class HeroBanner extends StatelessWidget {
  final VoidCallback? onPressed;

  const HeroBanner({super.key, this.onPressed});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: 70,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
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
      ),
      child: Row(
        children: [
          const Icon(
            Icons.auto_awesome,
            color: AshColors.boneWhite,
            size: 22,
          ),
          const SizedBox(width: 9),
          const Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'SoloForge AI',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: AshColors.boneWhite,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  'Create content faster',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: AshColors.smokeSilver,
                    fontSize: 10,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            height: 40,
            child: FilledButton.icon(
              onPressed: onPressed,
              icon: const Icon(Icons.emoji_emotions_outlined, size: 16),
              label: const Text(
                'สร้างสติ๊กเกอร์',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 11),
              ),
              style: FilledButton.styleFrom(
                backgroundColor: AshColors.boneWhite,
                foregroundColor: AshColors.oxblood,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
