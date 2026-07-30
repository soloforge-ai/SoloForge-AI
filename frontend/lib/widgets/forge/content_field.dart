import 'package:flutter/material.dart';

class ContentField extends StatelessWidget {
  final String label;
  final String hint;
  final TextEditingController controller;
  final int maxLines;

  /// ใช้สำหรับ Prompt Studio
  /// true = อ่านอย่างเดียว
  /// false = แก้ไขได้ (ค่าเริ่มต้น)
  final bool readOnly;

  const ContentField({
    super.key,
    required this.label,
    required this.hint,
    required this.controller,
    this.maxLines = 3,
    this.readOnly = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),

        const SizedBox(height: 8),

        TextField(
          controller: controller,
          readOnly: readOnly,
          maxLines: maxLines,
          decoration: InputDecoration(
            hintText: hint,
            border: const OutlineInputBorder(),
          ),
        ),
      ],
    );
  }
}