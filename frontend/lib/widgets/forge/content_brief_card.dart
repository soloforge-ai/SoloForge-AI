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
  static const _angles = ['Best Value', 'Problem → Solution', 'Key Benefit', 'Lifestyle'];
  static const _tones = ['Engaging', 'Friendly', 'Premium', 'Direct'];

  Widget _selector(
    BuildContext context,
    String label,
    String value,
    List<String> options,
    ValueChanged<String> onChanged,
  ) {
    return Expanded(
      child: DropdownButtonFormField<String>(
        initialValue: value,
        decoration: InputDecoration(labelText: label),
        items: options
            .map((option) => DropdownMenuItem(value: option, child: Text(option)))
            .toList(),
        onChanged: (next) {
          if (next != null) onChanged(next);
        },
      ),
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
            Row(
              children: [
                _selector(context, 'Goal', brief.goal, _goals, onGoalChanged),
                const SizedBox(width: 12),
                _selector(context, 'Angle', brief.angle, _angles, onAngleChanged),
                const SizedBox(width: 12),
                _selector(context, 'Tone', brief.tone, _tones, onToneChanged),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
