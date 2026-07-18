import 'package:flutter/material.dart';

class CategoryFilter extends StatelessWidget {
  final String selected;
  final Function(String) onSelected;

  const CategoryFilter({
    super.key,
    required this.selected,
    required this.onSelected,
  });

  final List<String> categories = const [
    "All",
    "Squishy",
    "Beauty",
    "Home Decor",
    "Shopee Food",
  ];

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 45,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: categories.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final category = categories[index];

          final isSelected = category == selected;

          return ChoiceChip(
            label: Text(category),
            selected: isSelected,
            onSelected: (_) => onSelected(category),
          );
        },
      ),
    );
  }
}