import 'package:flutter/material.dart';

class CategoryFilterBar extends StatelessWidget {
  const CategoryFilterBar({
    super.key,
    required this.categories,
    required this.selectedCategory,
    required this.onSelected,
  });

  final List<String> categories;
  final String selectedCategory;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 44,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: categories.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final category = categories[index];
          final selected = category == selectedCategory;

          return FilterChip(
            label: Text(category),
            selected: selected,
            onSelected: (_) => onSelected(category),
            showCheckmark: false,
            selectedColor: Colors.deepPurple,
            backgroundColor: const Color(0xFF2A2630),
            labelStyle: TextStyle(
              color: selected ? Colors.white : Colors.white70,
              fontWeight: selected ? FontWeight.bold : FontWeight.normal,
            ),
            side: BorderSide(
              color: selected
                  ? Colors.deepPurpleAccent
                  : Colors.grey.shade700,
            ),
          );
        },
      ),
    );
  }
}