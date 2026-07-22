import 'package:flutter/material.dart';

import '../../ai/platforms.dart';
import 'content_field.dart';

class ContentStudio extends StatelessWidget {
  final int selectedPlatform;

  final List<PlatformType> platforms;

  final ValueChanged<int> onPlatformChanged;

  final Future<void> Function() onGenerate;

  final VoidCallback onCopy;

  final TextEditingController hookController;
  final TextEditingController captionController;
  final TextEditingController hashtagController;
  final TextEditingController ctaController;

  const ContentStudio({
    super.key,
    required this.selectedPlatform,
    required this.platforms,
    required this.onPlatformChanged,
    required this.onGenerate,
    required this.onCopy,
    required this.hookController,
    required this.captionController,
    required this.hashtagController,
    required this.ctaController,
  });

  String _platformName(PlatformType platform) {
    switch (platform) {
      case PlatformType.facebook:
        return "Facebook";

      case PlatformType.tiktok:
        return "TikTok";

      case PlatformType.instagram:
        return "Instagram";

      case PlatformType.lemon8:
        return "Lemon8";

      case PlatformType.youtube:
        return "YouTube";

      case PlatformType.x:
        return "X";
    }
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
              "Content Studio",
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 16),

            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: List.generate(
                platforms.length,
                (index) {
                  return ChoiceChip(
                    label: Text(
                      _platformName(platforms[index]),
                    ),
                    selected: selectedPlatform == index,
                    onSelected: (_) {
                      onPlatformChanged(index);
                    },
                  );
                },
              ),
            ),

            const SizedBox(height: 24),

            ContentField(
              label: "Hook",
              hint: "AI จะสร้าง Hook ที่นี่",
              controller: hookController,
            ),

            const SizedBox(height: 16),

            ContentField(
              label: "Caption",
              hint: "AI จะสร้าง Caption ที่นี่",
              controller: captionController,
              maxLines: 5,
            ),

            const SizedBox(height: 16),

            ContentField(
              label: "Hashtags",
              hint: "#shopee #affiliate",
              controller: hashtagController,
            ),

            const SizedBox(height: 16),

            ContentField(
              label: "CTA",
              hint: "กดลิงก์เพื่อดูสินค้า",
              controller: ctaController,
            ),

            const SizedBox(height: 24),

            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: onGenerate,
                icon: const Icon(Icons.auto_awesome),
                label: const Text("Generate AI"),
              ),
            ),

            const SizedBox(height: 12),

            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: onCopy,
                icon: const Icon(Icons.copy),
                label: const Text("Copy All"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}