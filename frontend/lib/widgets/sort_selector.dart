import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';

enum SortType {
  miniBossScore,
  soldScore,
  priceScore,
  commissionScore,
}

class SortSelector extends StatelessWidget {
  final SortType value;
  final ValueChanged<SortType> onChanged;

  const SortSelector({
    super.key,
    required this.value,
    required this.onChanged,
  });

  String _label(SortType type) {
    switch (type) {
      case SortType.miniBossScore:
        return 'MiniBoss';
      case SortType.soldScore:
        return 'Sold';
      case SortType.priceScore:
        return 'Price';
      case SortType.commissionScore:
        return 'Commission';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      margin: EdgeInsets.zero,
      color: AshColors.blackPlum,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: AshColors.indigoMist.withValues(alpha: 0.7)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10),
        child: Row(
          children: [
            const Icon(Icons.star_rounded, color: AshColors.velvetRed, size: 18),
            const SizedBox(width: 6),
            const Text(
              'Sort',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12),
            ),
            const Spacer(),
            DropdownButtonHideUnderline(
              child: DropdownButton<SortType>(
                value: value,
                isDense: true,
                borderRadius: BorderRadius.circular(14),
                items: SortType.values.map((e) {
                  return DropdownMenuItem(
                    value: e,
                    child: Text(_label(e), style: const TextStyle(fontSize: 12)),
                  );
                }).toList(),
                onChanged: (v) {
                  if (v != null) onChanged(v);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
