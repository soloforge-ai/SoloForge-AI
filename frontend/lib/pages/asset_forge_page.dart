import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const String assetForgeApiUrl = String.fromEnvironment(
  'ASSET_FORGE_API_URL',
  defaultValue: '',
);

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
  double progress = 0.0;
  String status = 'Ready';
  String? errorMessage;
  List<String> generatedFiles = const [];

  final TextEditingController messageController = TextEditingController();

  bool get hasBackend => assetForgeApiUrl.trim().isNotEmpty;

  @override
  void dispose() {
    messageController.dispose();
    super.dispose();
  }

  List<String> _messages() {
    return messageController.text
        .split(RegExp(r'[,\n]'))
        .map((value) => value.trim())
        .where((value) => value.isNotEmpty)
        .toList();
  }

  Future<void> _simulatePipeline() async {
    final steps = <String>[
      'Preparing prompt...',
      'Generating image...',
      'Removing background...',
      'Splitting stickers...',
      'Naming files...',
      'Creating asset pack...',
    ];

    for (int i = 0; i < steps.length; i++) {
      await Future.delayed(const Duration(milliseconds: 600));
      if (!mounted) return;

      setState(() {
        status = steps[i];
        progress = (i + 1) / steps.length;
      });
    }

    if (!mounted) return;
    setState(() {
      isGenerating = false;
      status = 'Asset Pack Ready!';
      progress = 1.0;
      generatedFiles = List<String>.generate(
        quantity,
        (index) =>
            '${(index + 1).toString().padLeft(2, '0')}_${character.toLowerCase()}_sticker.png',
      );
    });
  }

  Future<void> _generateWithBackend() async {
    final baseUrl = assetForgeApiUrl.trim().replaceFirst(RegExp(r'/$'), '');

    setState(() {
      status = 'Connecting to Asset Forge server...';
      progress = 0.1;
    });

    final response = await http
        .post(
          Uri.parse('$baseUrl/v1/asset-forge/generate'),
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode({
            'character': character,
            'product': product,
            'theme': theme,
            'style': style,
            'quantity': quantity,
            'messages': _messages(),
          }),
        )
        .timeout(const Duration(minutes: 5));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      String message = 'Asset Forge server returned ${response.statusCode}.';
      try {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        message = body['detail']?.toString() ?? message;
      } catch (_) {
        // Keep the friendly fallback message.
      }
      throw Exception(message);
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final files = (body['files'] as List<dynamic>? ?? const [])
        .map((value) => value.toString())
        .toList();

    if (!mounted) return;
    setState(() {
      progress = 1.0;
      generatedFiles = files;
      status = 'Asset Pack Ready!';
      isGenerating = false;
    });
  }

  Future<void> generateAssets() async {
    if (isGenerating) return;

    setState(() {
      isGenerating = true;
      progress = 0.0;
      status = hasBackend ? 'Starting real pipeline...' : 'Preparing...';
      errorMessage = null;
      generatedFiles = const [];
    });

    try {
      if (hasBackend) {
        await _generateWithBackend();
      } else {
        await _simulatePipeline();
      }
    } on TimeoutException {
      if (!mounted) return;
      setState(() {
        isGenerating = false;
        status = 'Generation timed out';
        errorMessage = 'เซิร์ฟเวอร์ใช้เวลานานเกินไป ลองใหม่อีกครั้ง';
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        isGenerating = false;
        status = 'Generation failed';
        errorMessage = error.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Widget buildDropdown({
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
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          initialValue: value,
          decoration: InputDecoration(
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 14,
              vertical: 12,
            ),
          ),
          items: items
              .map(
                (item) => DropdownMenuItem<String>(
                  value: item,
                  child: Text(item),
                ),
              )
              .toList(),
          onChanged: isGenerating ? null : onChanged,
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Asset Forge'),
        centerTitle: true,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'SoloForge Asset Forge',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        hasBackend
                            ? 'Real AI pipeline connected.'
                            : 'MVP simulation mode — backend not connected yet.',
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 20),

              buildDropdown(
                label: 'Character',
                value: character,
                items: const ['Pearli', 'Aira', 'CEO'],
                onChanged: (value) {
                  if (value != null) setState(() => character = value);
                },
              ),

              const SizedBox(height: 16),

              buildDropdown(
                label: 'Product',
                value: product,
                items: const ['Sticker', 'Wallpaper', 'Social Media'],
                onChanged: (value) {
                  if (value != null) setState(() => product = value);
                },
              ),

              const SizedBox(height: 16),

              buildDropdown(
                label: 'Theme',
                value: theme,
                items: const [
                  'Healing & Encouragement',
                  'Love',
                  'Abundance',
                  'Manifestation',
                  'Good Morning',
                ],
                onChanged: (value) {
                  if (value != null) setState(() => theme = value);
                },
              ),

              const SizedBox(height: 16),

              buildDropdown(
                label: 'Style',
                value: style,
                items: const [
                  'Cute 3D Chibi',
                  'Cute 2D',
                  'Luxury',
                  'Celestial',
                ],
                onChanged: (value) {
                  if (value != null) setState(() => style = value);
                },
              ),

              const SizedBox(height: 20),

              Text(
                'Quantity: $quantity',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),

              Slider(
                value: quantity.toDouble(),
                min: 4,
                max: 24,
                divisions: 5,
                label: '$quantity',
                onChanged: isGenerating
                    ? null
                    : (value) => setState(() => quantity = value.round()),
              ),

              const SizedBox(height: 10),

              TextField(
                controller: messageController,
                enabled: !isGenerating,
                maxLines: 3,
                decoration: InputDecoration(
                  labelText: 'Sticker messages',
                  hintText: 'เช่น สู้ ๆ นะ, ขอบคุณนะ, รักนะ',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),

              const SizedBox(height: 24),

              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Icon(
                            isGenerating
                                ? Icons.auto_awesome
                                : Icons.check_circle_outline,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              status,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          Text('${(progress * 100).round()}%'),
                        ],
                      ),
                      const SizedBox(height: 12),
                      LinearProgressIndicator(
                        value: progress,
                        minHeight: 8,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      if (errorMessage != null) ...[
                        const SizedBox(height: 12),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            errorMessage!,
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.error,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 20),

              SizedBox(
                height: 52,
                child: ElevatedButton.icon(
                  onPressed: isGenerating ? null : generateAssets,
                  icon: Icon(
                    isGenerating
                        ? Icons.hourglass_top
                        : Icons.auto_awesome,
                  ),
                  label: Text(
                    isGenerating ? 'Generating...' : 'Generate Asset Pack',
                  ),
                ),
              ),

              if (generatedFiles.isNotEmpty) ...[
                const SizedBox(height: 20),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Generated ${generatedFiles.length} files',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        ...generatedFiles.take(6).map(Text.new),
                        if (generatedFiles.length > 6)
                          Text('…and ${generatedFiles.length - 6} more'),
                      ],
                    ),
                  ),
                ),
              ],

              const SizedBox(height: 20),

              Card(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Current Configuration',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 10),
                      Text('Character: $character'),
                      Text('Product: $product'),
                      Text('Theme: $theme'),
                      Text('Style: $style'),
                      Text('Quantity: $quantity'),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
