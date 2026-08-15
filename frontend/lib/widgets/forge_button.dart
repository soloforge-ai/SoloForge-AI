import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';

class ForgeButton extends StatelessWidget {
  const ForgeButton({
    super.key,
    required this.onPressed,
  });

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 124,
      height: 40,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          gradient: const LinearGradient(
            colors: [
              AshColors.deepIndigo,
              AshColors.oxblood,
            ],
          ),
          boxShadow: const [
            BoxShadow(
              color: Color(0x44541C2A),
              blurRadius: 12,
              offset: Offset(0, 4),
            ),
          ],
        ),
        child: FilledButton.icon(
          onPressed: onPressed,
          style: FilledButton.styleFrom(
            backgroundColor: Colors.transparent,
            shadowColor: Colors.transparent,
            foregroundColor: AshColors.boneWhite,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(22),
            ),
          ),
          icon: const Icon(
            Icons.auto_awesome,
            size: 16,
          ),
          label: const Text(
            "AI Forge",
            style: TextStyle(
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ),
    );
  }
}
