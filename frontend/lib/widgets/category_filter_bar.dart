import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';

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
      height: 40,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 2),
        itemCount: categories.length,
        separatorBuilder: (_, _) => const SizedBox(width: 6),
        itemBuilder: (context, index) {
          final category = categories[index];
          final selected = category == selectedCategory;

          return FilterChip(
            label: Text(
              category,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12),
            ),
            selected: selected,
            onSelected: (_) => onSelected(category),
            showCheckmark: false,
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            visualDensity: const VisualDensity(horizontal: -2, vertical: -2),
            selectedColor: AshColors.oxblood,
            backgroundColor: AshColors.blackPlum,
            side: BorderSide(
              color: selected
                  ? AshColors.velvetRed
                  : AshColors.indigoMist.withValues(alpha: 0.55),
            ),
            labelStyle: TextStyle(
              color: selected ? AshColors.boneWhite : AshColors.smokeSilver,
              fontWeight: selected ? FontWeight.bold : FontWeight.normal,
            ),
          );
        },
      ),
    );
  }
}
