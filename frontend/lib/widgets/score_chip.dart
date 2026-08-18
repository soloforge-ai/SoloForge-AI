import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';

class ScoreChip extends StatelessWidget {
  const ScoreChip({
    super.key,
    required this.label,
    required this.value,
    this.color = AshColors.deepIndigo,
  });

  final String label;
  final double value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 8,
        vertical: 4,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: color,
          width: 1,
        ),
      ),
      child: Text(
        "$label ${value.round()}",
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
