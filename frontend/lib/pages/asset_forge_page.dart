import 'package:flutter/material.dart';

class AssetForgePage extends StatefulWidget {
  const AssetForgePage({super.key});

  @override
  State<AssetForgePage> createState() => _AssetForgePageState();
}

class _AssetForgePageState extends State<AssetForgePage> {
  String character = 'Pearli';
  String product = 'Sticker';
  String theme = 'Healing & Encouragement';
  String style = 'Cute 3D Chibi';

  int quantity = 12;

  bool isGenerating = false;
  double progress = 0;

  String status = 'พร้อมสร้าง Asset Pack';

  final TextEditingController messagesController =
      TextEditingController(
    text:
        'สวัสดี\n'
        'ขอบคุณ\n'
        'รักนะ\n'
        'เป็นกำลังใจให้นะ\n'
        'กอด ๆ\n'
        'สู้ ๆ\n'
        'พักผ่อนด้วยนะ\n'
        'คิดถึงนะ\n'
        'ยิ้มไว้นะ\n'
        'เก่งมาก\n'
        'ขอให้วันนี้เป็นวันที่ดี\n'
        'ส่งพลังให้นะ',
  );

  @override
  void dispose() {
    messagesController.dispose();
    super.dispose();
  }

  Future<void> generateAssetPack() async {
    if (isGenerating) return;

    setState(() {
      isGenerating = true;
      progress = 0;
      status = 'กำลังเตรียม Prompt...';
    });

    final steps = [
      'กำลังเตรียม Prompt...',
      'กำลังสร้างภาพ...',
      'กำลังเตรียม Asset...',
      'กำลังตัด Asset...',
      'กำลังตั้งชื่อไฟล์...',
      'Asset Pack พร้อมแล้ว!',
    ];

    for (int i = 0; i < steps.length; i++) {
      await Future.delayed(
        const Duration(milliseconds: 700),
      );

      if (!mounted) return;

      setState(() {
        status = steps[i];
        progress = (i + 1) / steps.length;
      });
    }

    if (!mounted) return;

    setState(() {
      isGenerating = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'สร้าง Asset Pack สำเร็จ! '
          'ตอนนี้เป็น Demo Pipeline',
        ),
      ),
    );
  }

  Widget buildSelectField({
    required String label,
    required String value,
    required List<String> items,
    required ValueChanged<String?> onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 15,
          ),
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          value: value,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            contentPadding: EdgeInsets.symmetric(
              horizontal: 14,
              vertical: 12,
            ),
          ),
          items: items.map((item) {
            return DropdownMenuItem<String>(
              value: item,
              child: Text(item),
            );
          }).toList(),
          onChanged: onChanged,
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('✨ Asset Forge'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment:
                CrossAxisAlignment.stretch,
            children: [
              // HEADER
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Asset Forge',
                        style: TextStyle(
                          fontSize: 26,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'สร้าง Asset Pack จาก Character + Theme + Style',
                        style: TextStyle(
                          color: Colors.grey.shade600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // SETTINGS
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment:
                        CrossAxisAlignment.stretch,
                    children: [
                      const Text(
                        '⚙️ Asset Settings',
                        style: TextStyle(
                          fontSize: 19,
                          fontWeight: FontWeight.bold,
                        ),
                      ),

                      const SizedBox(height: 18),

                      // CHARACTER
                      buildSelectField(
                        label: 'Character',
                        value: character,
                        items: const [
                          'Pearli',
                          'Aira',
                        ],
                        onChanged: (value) {
                          if (value == null) return;

                          setState(() {
                            character = value;
                          });
                        },
                      ),

                      const SizedBox(height: 16),

                      // PRODUCT
                      buildSelectField(
                        label: 'Product',
                        value: product,
                        items: const [
                          'Sticker',
                          'Social Post',
                          'Wallpaper',
                          'Emoji',
                        ],
                        onChanged: (value) {
                          if (value == null) return;

                          setState(() {
                            product = value;
                          });
                        },
                      ),

                      const SizedBox(height: 16),

                      // THEME
                      buildSelectField(
                        label: 'Theme',
                        value: theme,
                        items: const [
                          'Healing & Encouragement',
                          'Love',
                          'Abundance',
                          'Motivation',
                        ],
                        onChanged: (value) {
                          if (value == null) return;

                          setState(() {
                            theme = value;
                          });
                        },
                      ),

                      const SizedBox(height: 16),

                      // STYLE
                      buildSelectField(
                        label: 'Style',
                        value: style,
                        items: const [
                          'Cute 3D Chibi',
                          'Soft Kawaii',
                          'Luxury Spiritual',
                        ],
                        onChanged: (value) {
                          if (value == null) return;

                          setState(() {
                            style = value;
                          });
                        },
                      ),

                      const SizedBox(height: 18),

                      // QUANTITY
                      const Text(
                        'Quantity',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),

                      Row(
                        children: [
                          Expanded(
                            child: Slider(
                              value: quantity.toDouble(),
                              min: 4,
                              max: 24,
                              divisions: 5,
                              label: '$quantity',
                              onChanged: (value) {
                                setState(() {
                                  quantity = value.round();
                                });
                              },
                            ),
                          ),
                          SizedBox(
                            width: 45,
                            child: Text(
                              '$quantity',
                              textAlign: TextAlign.center,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 12),

                      // MESSAGES
                      const Text(
                        'Messages',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),

                      const SizedBox(height: 8),

                      TextField(
                        controller:
