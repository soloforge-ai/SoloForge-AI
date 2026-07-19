import 'package:flutter/material.dart';

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

  @override
  Widget build(BuildContext context) {
    return DropdownButton<SortType>(
      value: value,
      isExpanded: true,
      underline: const SizedBox(),
      items: const [
        DropdownMenuItem(
          value: SortType.miniBossScore,
          child: Text('⭐ MiniBoss Score'),
        ),
        DropdownMenuItem(
          value: SortType.soldScore,
          child: Text('🛒 Sold Score'),
        ),
        DropdownMenuItem(
          value: SortType.priceScore,
          child: Text('💵 Price Score'),
        ),
        DropdownMenuItem(
          value: SortType.commissionScore,
          child: Text('💰 Commission Score'),
        ),
      ],
      onChanged: (value) {
        if (value != null) {
          onChanged(value);
        }
      },
    );
  }
}
