import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../core/theme/app_theme.dart';

const String stickerForgeApiUrl = String.fromEnvironment(
  'ASSET_FORGE_API_URL',
  defaultValue: 'https://soloforge-asset-forge.onrender.com',
);

class StickerForgePage extends StatefulWidget {
  const StickerForgePage({super.key});

  @override
  State<StickerForgePage> createState() => _StickerForgePageState();
}

class _StickerForgePageState extends State<StickerForgePage> {
  String character = 'CEO';
  String theme = 'Healing & Encouragement';
  String style = 'Cute 3D Chibi';
  int quantity = 12;

  final messageController = TextEditingController();

  bool generating = false;
  double progress = 0;
  String status = 'Ready to forge your sticker pack.';
  String? errorMessage;
  List<String> generatedFiles = const [];
  Uint8List? previewBytes;

  @override
  void dispose() {
    messageController.dispose();
    super.dispose();
  }

  List<String> get messages => messageController.text
      .split(RegExp(r'[,\n]'))
      .map((value) => value.trim())
      .where((value) => value.isNotEmpty)
      .toList();

  Future<void> generateStickers() async {
    if (generating) return;

    setState(() {
      generating = true;
      progress = 0.08;
      status = 'Connecting to Asset Forge...';
      errorMessage = null;
      generatedFiles = const [];
      previewBytes = null;
    });

    try {
      final baseUrl = stickerForgeApiUrl.replaceFirst(RegExp(r'/$'), '');
      final responseFuture = http.post(
        Uri.parse('$baseUrl/v1/asset-forge/generate'),
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode({
          'character': character,
          'product': 'Sticker',
          'theme': theme,
          'style': style,
          'quantity': quantity,
          'messages': messages,
        }),
      ).timeout(const Duration(minutes: 5));

      setState(() {
        progress = 0.18;
        status = 'Generating sticker sheet...';
      });

      final response = await responseFuture;

      if (response.statusCode < 200 || response.statusCode >= 300) {
        String message = 'Asset Forge returned ${response.statusCode}.';
        try {
          final body = jsonDecode(response.body) as Map<String, dynamic>;
          message = body['detail']?.toString() ?? message;
        } catch (_) {}
        throw Exception(message);
      }

      setState(() {
        progress = 0.82;
        status = 'Processing transparent stickers...';
      });

      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final files = (body['files'] as List<dynamic>? ?? const [])
          .map((value) => value.toString())
          .toList();
      final source = body['source_image_base64']?.toString();

      if (!mounted) return;
      setState(() {
        progress = 1;
        status = 'Sticker Pack Ready!';
        generating = false;
        generatedFiles = files;
        previewBytes = source == null || source.isEmpty
            ? null
            : base64Decode(source);
      });
    } on TimeoutException {
      if (!mounted) return;
      setState(() {
        generating = false;
        status = 'Generation timed out';
        errorMessage = 'เซิร์ฟเวอร์ใช้เวลานานเกินไป ลองใหม่อีกครั้ง';
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        generating = false;
        status = 'Generation failed';
        errorMessage = error.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Widget _dropdown({
    required String label,
    required String value,
    required List<String> items,
    required ValueChanged<String?> onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          initialValue: value,
          decoration: const InputDecoration(),
          items: items
              .map((item) => DropdownMenuItem(value: item, child: Text(item)))
              .toList(),
          onChanged: generating ? null : onChanged,
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sticker Forge'),
        leading: const BackButton(),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  gradient: const LinearGradient(
                    colors: [
                      AshColors.blackPlum,
                      AshColors.deepIndigo,
                      AshColors.oxblood,
                    ],
                  ),
                  border: Border.all(color: AshColors.indigoMist),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'CREATE STICKERS',
                      style: TextStyle(
                        color: AshColors.boneWhite,
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    SizedBox(height: 6),
                    Text(
                      'Forge a ready-to-use sticker pack from one character.',
                      style: TextStyle(color: AshColors.smokeSilver),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _dropdown(
                        label: 'Character',
                        value: character,
                        items: const ['CEO', 'Pearli', 'Aira'],
                        onChanged: (value) {
                          if (value != null) setState(() => character = value);
                        },
                      ),
                      const SizedBox(height: 16),
                      _dropdown(
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
                      _dropdown(
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
                      const SizedBox(height: 14),
                      Text(
                        'Pack size: $quantity stickers',
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      Slider(
                        value: quantity.toDouble(),
                        min: 4,
                        max: 24,
                        divisions: 5,
                        label: '$quantity',
                        onChanged: generating
                            ? null
                            : (value) => setState(() => quantity = value.round()),
                      ),
                      TextField(
                        controller: messageController,
                        enabled: !generating,
                        maxLines: 4,
                        decoration: const InputDecoration(
                          labelText: 'Sticker messages',
                          hintText: 'เช่น สู้ ๆ นะ, ขอบคุณนะ, รักนะ',
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Icon(
                            generating ? Icons.auto_awesome : Icons.check_circle_outline,
                            color: generating
                                ? AshColors.indigoMist
                                : AshColors.boneWhite,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              status,
                              style: const TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                          Text('${(progress * 100).round()}%'),
                        ],
                      ),
                      const SizedBox(height: 10),
                      LinearProgressIndicator(value: progress, minHeight: 7),
                      if (errorMessage != null) ...[
                        const SizedBox(height: 10),
                        Text(
                          errorMessage!,
                          style: TextStyle(color: Theme.of(context).colorScheme.error),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 14),
              SizedBox(
                height: 54,
                child: FilledButton.icon(
                  onPressed: generating ? null : generateStickers,
                  icon: Icon(generating ? Icons.hourglass_top : Icons.auto_awesome),
                  label: Text(generating ? 'Generating...' : 'Generate Sticker Pack'),
                ),
              ),
              if (previewBytes != null) ...[
                const SizedBox(height: 18),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Generated Sheet',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 10),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(14),
                          child: Image.memory(previewBytes!, fit: BoxFit.contain),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              if (generatedFiles.isNotEmpty) ...[
                const SizedBox(height: 14),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${generatedFiles.length} sticker files generated',
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 8),
                        ...generatedFiles.take(8).map(
                              (name) => Padding(
                                padding: const EdgeInsets.symmetric(vertical: 3),
                                child: Row(
                                  children: [
                                    const Icon(Icons.image_outlined, size: 18),
                                    const SizedBox(width: 8),
                                    Expanded(child: Text(name)),
                                  ],
                                ),
                              ),
                            ),
                        if (generatedFiles.length > 8)
                          Text('…and ${generatedFiles.length - 8} more'),
                        const SizedBox(height: 8),
                        const Text(
                          'Next step: connect the ZIP/share action so the pack can be exported directly to the device.',
                          style: TextStyle(color: AshColors.smokeSilver, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
