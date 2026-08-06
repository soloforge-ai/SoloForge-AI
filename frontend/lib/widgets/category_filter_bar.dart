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
      height: 46,
      child: ScrollConfiguration(
        behavior: const MaterialScrollBehavior().copyWith(
          scrollbars: true,
        ),
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          physics: const BouncingScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 4),
          itemCount: categories.length,
          separatorBuilder: (_, _) => const SizedBox(width: 8),
          itemBuilder: (context, index) {
            final category = categories[index];
            final selected = category == selectedCategory;

            return FilterChip(
              label: Text(
                category,
                overflow: TextOverflow.ellipsis,
              ),
              selected: selected,
              onSelected: (_) => onSelected(category),
              showCheckmark: false,
              materialTapTargetSize:
                  MaterialTapTargetSize.shrinkWrap,
              visualDensity: VisualDensity.compact,
              selectedColor: Colors.deepPurple,
              backgroundColor: const Color(0xFF2A2630),
              side: BorderSide(
                color: selected
                    ? Colors.deepPurpleAccent
                    : Colors.grey.shade700,
              ),
              labelStyle: TextStyle(
                color: selected
                    ? Colors.white
                    : Colors.white70,
                fontWeight: selected
                    ? FontWeight.bold
                    : FontWeight.normal,
              ),
            );
          },
        ),
      ),
    );
  }
}