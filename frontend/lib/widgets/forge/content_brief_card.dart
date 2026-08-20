import 'package:flutter/material.dart';

import '../../models/content_brief.dart';

class ContentBriefCard extends StatelessWidget {
  final ContentBrief brief;
  final ValueChanged<String> onGoalChanged;
  final ValueChanged<String> onAngleChanged;
  final ValueChanged<String> onToneChanged;

  const ContentBriefCard({
    super.key,
    required this.brief,
    required this.onGoalChanged,
    required this.onAngleChanged,
    required this.onToneChanged,
  });

  static const _goals = ['Sell', 'Educate', 'Engage'];
  static const _angles = [
    'Best Value',
    'Problem → Solution',
    'Key Benefit',
    'Lifestyle',
  ];
  static const _tones = ['Engaging', 'Friendly', 'Premium', 'Direct'];

  Widget _selector(
    BuildContext context,
    String label,
    String value,
    List<String> options,
    ValueChanged<String> onChanged,
  ) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label),
      items: options
          .map(
            (option) => DropdownMenuItem(
              value: option,
              child: Text(option, overflow: TextOverflow.ellipsis),
            ),
          )
          .toList(),
      onChanged: (next) {
        if (next != null) onChanged(next);
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Content Brief',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            const Text('กำหนดเป้าหมายก่อนให้ SoloForge สร้างคอนเทนต์'),
            const SizedBox(height: 16),
            LayoutBuilder(
              builder: (context, constraints) {
                final selectors = [
                  _selector(
                    context,
                    'Goal',
                    brief.goal,
                    _goals,
                    onGoalChanged,
                  ),
                  _selector(
                    context,
                    'Angle',
                    brief.angle,
                    _angles,
                    onAngleChanged,
                  ),
                  _selector(
                    context,
                    'Tone',
                    brief.tone,
                    _tones,
                    onToneChanged,
                  ),
                ];

                if (constraints.maxWidth < 700) {
                  return Column(
                    children: [
                      selectors[0],
                      const SizedBox(height: 12),
                      selectors[1],
                      const SizedBox(height: 12),
                      selectors[2],
                    ],
                  );
                }

                return Row(
                  children: [
                    Expanded(child: selectors[0]),
                    const SizedBox(width: 12),
                    Expanded(child: selectors[1]),
                    const SizedBox(width: 12),
                    Expanded(child: selectors[2]),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
