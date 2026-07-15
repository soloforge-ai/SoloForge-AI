import 'package:flutter/material.dart';

enum SortType {
  score,
  commission,
  rating,
  price,
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
          value: SortType.score,
          child: Text("⭐ Best Score"),
        ),
        DropdownMenuItem(
          value: SortType.commission,
          child: Text("💰 Highest Commission"),
        ),
        DropdownMenuItem(
          value: SortType.rating,
          child: Text("⭐ Highest Rating"),
        ),
        DropdownMenuItem(
          value: SortType.price,
          child: Text("💵 Lowest Price"),
        ),
      ],
      onChanged: (v) {
        if (v != null) {
          onChanged(v);
        }
      },
    );
  }
}