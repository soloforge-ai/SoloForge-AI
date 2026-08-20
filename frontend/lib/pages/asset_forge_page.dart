import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../services/pollinations_session_service.dart';

class AssetForgePage extends StatefulWidget {
  const AssetForgePage({super.key, this.useBackend});

  final bool? useBackend;

  @override
  State<AssetForgePage> createState() => _AssetForgePageState();
}

class _AssetForgePageState extends State<AssetForgePage> {
  String character = 'CEO';
  String product = 'Sticker';
  String theme = 'Healing & Encouragement';
  String style = 'Cute 3D Chibi';

  int quantity = 12;
  bool isGenerating = false;
  bool isSaving = false;
  bool isConnectingPollinations = false;
  bool isPollinationsConnected = false;
  double progress = 0.0;
  String status = 'Ready';
  String pollinationsStatus = 'Not connected';
  String? errorMessage;
  List<String> generatedFiles = const [];
  String? zipBase64;
  String? sourceImageBase64;

  final TextEditingController messageController = TextEditingController();
  final PollinationsSessionService _pollinationsSession =
      PollinationsSessionService();

  bool get hasBackend =>
      widget.useBackend ?? assetForgeApiUrl.trim().isNotEmpty;

  @override
  void initState() {
    super.initState();
    if (hasBackend) {
      unawaited(_initializePollinations());
    }
  }

  Future<void> _initializePollinations() async {
    await _pollinationsSession.startListening(
      onCallback: _handlePollinationsCallback,
    );
    await _refreshPollinationsStatus();
  }

  Future<void> _handlePollinationsCallback(Uri uri) async {
    if (!_pollinationsSession.isPollinationsCallback(uri)) return;
    if (mounted) {
      setState(() {
        isConnectingPollinations = true;
        pollinationsStatus = 'Finishing connection...';
        errorMessage = null;
      });
    }

    try {
      final session = await _pollinationsSession.handleCallback(uri);
      if (!mounted) return;
      setState(() {
        isPollinationsConnected = session.connected;
        isConnectingPollinations = false;
        pollinationsStatus = session.connected ? 'Connected' : 'Not connected';
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        isPollinationsConnected = false;
        isConnectingPollinations = false;
        pollinationsStatus = 'Connection failed';
        errorMessage = error.toString();
      });
    }
  }

  Future<void> _refreshPollinationsStatus() async {
    try {
      final session = await _pollinationsSession.status();
      if (!mounted) return;
      setState(() {
        isPollinationsConnected = session.connected;
        pollinationsStatus = session.connected ? 'Connected' : 'Not connected';
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        isPollinationsConnected = false;
        pollinationsStatus = 'Not connected';
      });
    }
  }

  Future<void> _connectPollinations() async {
    if (isConnectingPollinations) return;
    setState(() {
      isConnectingPollinations = true;
      pollinationsStatus = 'Opening Pollinations...';
      errorMessage = null;
    });
    try {
      await _pollinationsSession.connect();
      if (!mounted) return;
      setState(() {
        pollinationsStatus = 'Waiting for authorization...';
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        isConnectingPollinations = false;
        pollinationsStatus = 'Connection failed';
        errorMessage = error.toString();
      });
    }
  }

  Future<void> _disconnectPollinations() async {
    setState(() {
      isConnectingPollinations = true;
      errorMessage = null;
    });
    try {
      await _pollinationsSession.disconnect();
    } finally {
      if (mounted) {
        setState(() {
          isConnectingPollinations = false;
          isPollinationsConnected = false;
          pollinationsStatus = 'Not connected';
        });
      }
    }
  }

  @override
  void dispose() {
    messageController.dispose();
    unawaited(_pollinationsSession.dispose());
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
    final authHeaders = await _pollinationsSession.authorizationHeaders();

    setState(() {
      status = 'Connecting to Asset Forge server...';
      progress = 0.1;
    });

    final response = await http
        .post(
          Uri.parse('$baseUrl/v1/asset-forge/generate'),
          headers: {
            'Content-Type': 'application/json',
            ...authHeaders,
          },
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

    if (response.statusCode == 401) {
      await _refreshPollinationsStatus();
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      String message = 'Asset Forge server returned ${response.statusCode}.';
      try {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        message = body['detail']?.toString() ?? message;
      } catch (_) {}
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
      zipBase64 = body['zip_base64']?.toString();
      sourceImageBase64 = body['source_image_base64']?.toString();
      status = 'Asset Pack Ready!';
      isGenerating = false;
    });
  }

  Future<void> _saveAndShareZip() async {
    if (zipBase64 == null || zipBase64!.isEmpty || isSaving) return;

    setState(() {
      isSaving = true;
      errorMessage = null;
    });

    try {
      final bytes = base64Decode(zipBase64!);
      final directory = await getTemporaryDirectory();
      final safeCharacter = character.toLowerCase().replaceAll(
            RegExp(r'[^a-z0-9]+'),
            '_',
          );
      final filename =
          '${safeCharacter}_${product.toLowerCase()}_${quantity}pack.zip';
      final file = File('${directory.path}/$filename');
      await file.writeAsBytes(bytes, flush: true);

      await SharePlus.instance.share(
        ShareParams(
          files: [XFile(file.path)],
          title: 'SoloForge Asset Pack',
          text: 'SoloForge Asset Forge — $filename',
        ),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        errorMessage = 'บันทึกไฟล์ไม่สำเร็จ: $error';
      });
    } finally {
      if (mounted) {
        setState(() => isSaving = false);
      }
    }
  }

  Future<void> _downloadZip() async {
    await _saveAndShareZip();
  }

  Future<void> generateAssets() async {
    if (isGenerating) return;
    if (hasBackend && !isPollinationsConnected) {
      setState(() {
        errorMessage = 'Connect Pollinations before generating assets.';
      });
      return;
    }

    setState(() {
      isGenerating = true;
      progress = 0.0;
      status = hasBackend ? 'Starting real pipeline...' : 'Preparing...';
      errorMessage = null;
      generatedFiles = const [];
      zipBase64 = null;
      sourceImageBase64 = null;
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
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
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

  Widget _buildPollinationsCard() {
    final connected = isPollinationsConnected;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(
                  connected ? Icons.cloud_done_outlined : Icons.cloud_off_outlined,
                ),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text(
                    'Pollinations',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
                Text(pollinationsStatus),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              connected
                  ? 'Your Pollinations account will be used for generation.'
                  : 'Connect your Pollinations account before generating real assets.',
              style: const TextStyle(fontSize: 13),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: isConnectingPollinations
                  ? null
                  : connected
                      ? _disconnectPollinations
                      : _connectPollinations,
              icon: Icon(connected ? Icons.link_off : Icons.link),
              label: Text(
                isConnectingPollinations
                    ? 'Please wait...'
                    : connected
                        ? 'Disconnect Pollinations'
                        : 'Connect Pollinations',
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Asset Forge'), centerTitle: true),
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
              if (hasBackend) ...[
                const SizedBox(height: 12),
                _buildPollinationsCard(),
              ],
              const SizedBox(height: 20),
              buildDropdown(
                label: 'Character',
                value: character,
                items: const ['CEO', 'Pearli', 'Aira'],
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
                              style:
                                  const TextStyle(fontWeight: FontWeight.bold),
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
                  onPressed: isGenerating ||
                          (hasBackend && !isPollinationsConnected)
                      ? null
                      : generateAssets,
                  icon: Icon(
                    isGenerating ? Icons.hourglass_top : Icons.auto_awesome,
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
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          'Generated ${generatedFiles.length} files',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        ...generatedFiles.take(6).map(
                              (name) => Padding(
                                padding:
                                    const EdgeInsets.symmetric(vertical: 3),
                                child: Row(
                                  children: [
                                    const Icon(
                                      Icons.image_outlined,
                                      size: 18,
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(child: Text(name)),
                                  ],
                                ),
                              ),
                            ),
                        if (generatedFiles.length > 6)
                          Text('…and ${generatedFiles.length - 6} more'),
                        const SizedBox(height: 16),
                        SizedBox(
                          height: 50,
                          child: ElevatedButton.icon(
                            onPressed: isSaving ? null : _downloadZip,
                            icon: Icon(
                              isSaving
                                  ? Icons.hourglass_top
                                  : Icons.download_rounded,
                            ),
                            label: Text(
                              isSaving
                                  ? 'Preparing ZIP...'
                                  : 'Download Asset Pack (.ZIP)',
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'ไฟล์ ZIP จะเปิดเมนูแชร์/บันทึกของเครื่อง เพื่อเลือก Drive, Files หรือแอปปลายทางที่ต้องการ',
                          style: TextStyle(fontSize: 12),
                        ),
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
