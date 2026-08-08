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

  String _label(SortType type) {
    switch (type) {
      case SortType.miniBossScore:
        return "MiniBoss";
      case SortType.soldScore:
        return "Sold";
      case SortType.priceScore:
        return "Price";
      case SortType.commissionScore:
        return "Commission";
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Theme.of(context).cardColor,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: 12,
          vertical: 8,
        ),
        child: Row(
          children: [
            const Icon(
              Icons.star,
              color: Colors.amber,
            ),

            const SizedBox(width: 8),

            const Text(
              "Sort by",
              style: TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),

            const Spacer(),

            DropdownButtonHideUnderline(
              child: DropdownButton<SortType>(
                value: value,
                borderRadius: BorderRadius.circular(16),
                items: SortType.values.map((e) {
                  return DropdownMenuItem(
                    value: e,
                    child: Text(_label(e)),
                  );
                }).toList(),
                onChanged: (v) {
                  if (v != null) {
                    onChanged(v);
                  }
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}