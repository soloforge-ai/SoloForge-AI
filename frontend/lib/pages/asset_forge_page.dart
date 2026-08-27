import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/asset_forge_character_config.dart';
import '../services/pollinations_session_service.dart';

class AssetForgePage extends StatefulWidget {
  const AssetForgePage({super.key, this.useBackend});

  final bool? useBackend;

  @override
  State<AssetForgePage> createState() => _AssetForgePageState();
}

class _AssetForgePageState extends State<AssetForgePage> {
  static final Uri _pollinationsDashboard = Uri.parse('https://enter.pollinations.ai/');

  String characterType = 'Cat';
  String primaryColor = 'Blue';
  String product = 'Sticker';
  String theme = 'Healing & Encouragement';
  String style = 'Cute 3D Chibi';
  int quantity = 4;

  bool isGenerating = false;
  bool isSaving = false;
  bool isConnectingPollinations = false;
  bool isPollinationsConnected = false;
  bool showEarnPollenHint = false;
  double progress = 0.0;
  String status = 'Ready';
  String pollinationsStatus = 'Not connected';
  String? errorMessage;
  List<String> generatedFiles = const [];
  String? zipBase64;

  final TextEditingController messageController = TextEditingController();
  final PollinationsSessionService _pollinationsSession = PollinationsSessionService();

  bool get hasBackend => widget.useBackend ?? assetForgeApiUrl.trim().isNotEmpty;
  bool get builderEnabled => !isGenerating && (!hasBackend || isPollinationsConnected);

  AssetForgeCharacterConfig get characterConfig => AssetForgeCharacterConfig(
        characterType: characterType,
        primaryColor: primaryColor,
      );

  @override
  void initState() {
    super.initState();
    if (hasBackend) {
      unawaited(_initializePollinations());
    }
  }

  Future<void> _initializePollinations() async {
    await _pollinationsSession.startListening(onCallback: _handlePollinationsCallback);
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
      setState(() => pollinationsStatus = 'Waiting for authorization...');
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

  Future<void> _openEarnPollen() async {
    final opened = await launchUrl(_pollinationsDashboard, mode: LaunchMode.externalApplication);
    if (!opened && mounted) {
      setState(() {
        errorMessage = 'เปิด Pollinations dashboard ไม่สำเร็จ กรุณาเปิด enter.pollinations.ai ในเบราว์เซอร์';
      });
    }
  }

  List<String> _messages() {
    return messageController.text
        .split(RegExp(r'[,\n]'))
        .map((value) => value.trim())
        .where((value) => value.isNotEmpty)
        .toList();
  }

  Future<void> _simulatePipeline() async {
    for (final step in <String>[
      'Preparing prompt...',
      'Generating image...',
      'Removing background...',
      'Splitting stickers...',
      'Creating asset pack...',
    ]) {
      await Future.delayed(const Duration(milliseconds: 250));
      if (!mounted) return;
      setState(() {
        status = step;
        progress = (progress + 0.2).clamp(0.0, 1.0);
      });
    }
    if (!mounted) return;
    setState(() {
      isGenerating = false;
      status = 'Asset Pack Ready!';
      progress = 1.0;
      generatedFiles = List.generate(quantity, (index) => '${(index + 1).toString().padLeft(2, '0')}_beta_sticker.png');
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
          headers: {'Content-Type': 'application/json', ...authHeaders},
          body: jsonEncode({
            'character': characterConfig.backendCharacter,
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
      if (AssetForgeCharacterConfig.isPollenPaymentFailure(
        statusCode: response.statusCode,
        message: message,
      )) {
        showEarnPollenHint = true;
      }
      throw Exception(message);
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final files = (body['files'] as List<dynamic>? ?? const []).map((value) => value.toString()).toList();

    if (!mounted) return;
    setState(() {
      progress = 1.0;
      generatedFiles = files;
      zipBase64 = body['zip_base64']?.toString();
      status = 'Asset Pack Ready!';
      isGenerating = false;
      showEarnPollenHint = false;
    });
  }

  Future<void> generateAssets() async {
    if (isGenerating) return;
    if (hasBackend && !isPollinationsConnected) {
      setState(() => errorMessage = 'Connect Pollinations before generating assets.');
      return;
    }

    setState(() {
      isGenerating = true;
      progress = 0.0;
      status = hasBackend ? 'Starting real pipeline...' : 'Preparing...';
      errorMessage = null;
      generatedFiles = const [];
      zipBase64 = null;
      showEarnPollenHint = false;
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

  Future<void> _saveAndShareZip() async {
    if (zipBase64 == null || zipBase64!.isEmpty || isSaving) return;
    setState(() {
      isSaving = true;
      errorMessage = null;
    });
    try {
      final bytes = base64Decode(zipBase64!);
      final directory = await getTemporaryDirectory();
      final safeCharacter = characterConfig.backendCharacter.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '_');
      final file = File('${directory.path}/${safeCharacter}_${quantity}pack.zip');
      await file.writeAsBytes(bytes, flush: true);
      await SharePlus.instance.share(
        ShareParams(
          files: [XFile(file.path)],
          title: 'SoloForge Asset Pack',
          text: 'SoloForge Asset Forge — ${characterConfig.summary}',
        ),
      );
    } catch (error) {
      if (mounted) setState(() => errorMessage = 'บันทึกไฟล์ไม่สำเร็จ: $error');
    } finally {
      if (mounted) setState(() => isSaving = false);
    }
  }

  Widget _dropdown({
    required String label,
    required String value,
    required List<String> items,
    required ValueChanged<String?> onChanged,
  }) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      decoration: InputDecoration(labelText: label, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
      items: items.map((item) => DropdownMenuItem(value: item, child: Text(item))).toList(),
      onChanged: builderEnabled ? onChanged : null,
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
                Icon(connected ? Icons.cloud_done_outlined : Icons.cloud_off_outlined),
                const SizedBox(width: 10),
                const Expanded(child: Text('Pollinations', style: TextStyle(fontWeight: FontWeight.bold))),
                Text(pollinationsStatus),
              ],
            ),
            const SizedBox(height: 8),
            Text(connected
                ? 'Connected. Choose your character below, then generate with your Pollinations wallet.'
                : 'Connect Pollinations first. Character Builder unlocks after authorization.'),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: isConnectingPollinations
                  ? null
                  : connected
                      ? _disconnectPollinations
                      : _connectPollinations,
              icon: Icon(connected ? Icons.link_off : Icons.link),
              label: Text(isConnectingPollinations
                  ? 'Please wait...'
                  : connected
                      ? 'Disconnect Pollinations'
                      : 'Connect Pollinations'),
            ),
            if (connected) ...[
              const SizedBox(height: 8),
              TextButton.icon(
                onPressed: _openEarnPollen,
                icon: const Icon(Icons.task_alt),
                label: const Text('Earn Pollen with Quests'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    messageController.dispose();
    unawaited(_pollinationsSession.dispose());
    super.dispose();
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
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('SoloForge Asset Forge Beta', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                      SizedBox(height: 6),
                      Text('Connect → Build your character → Generate → Download'),
                    ],
                  ),
                ),
              ),
              if (hasBackend) ...[
                const SizedBox(height: 12),
                _buildPollinationsCard(),
              ],
              const SizedBox(height: 20),
              Text('Character Builder', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              _dropdown(
                label: 'Character type',
                value: characterType,
                items: const ['Cat', 'Dog', 'Bear', 'Rabbit', 'Robot', 'Human Mascot', 'CEO', 'Pearli', 'Aira'],
                onChanged: (value) {
                  if (value != null) setState(() => characterType = value);
                },
              ),
              const SizedBox(height: 12),
              _dropdown(
                label: 'Primary color',
                value: primaryColor,
                items: const ['Blue', 'Black', 'White', 'Pink', 'Red', 'Green', 'Purple', 'Yellow'],
                onChanged: (value) {
                  if (value != null) setState(() => primaryColor = value);
                },
              ),
              const SizedBox(height: 12),
              _dropdown(
                label: 'Style',
                value: style,
                items: const ['Cute 3D Chibi', 'Cute 2D', 'Cartoon', 'Luxury'],
                onChanged: (value) {
                  if (value != null) setState(() => style = value);
                },
              ),
              const SizedBox(height: 12),
              _dropdown(
                label: 'Theme',
                value: theme,
                items: const ['Healing & Encouragement', 'Love', 'Abundance', 'Good Morning'],
                onChanged: (value) {
                  if (value != null) setState(() => theme = value);
                },
              ),
              const SizedBox(height: 16),
              Text('Quantity: $quantity', style: const TextStyle(fontWeight: FontWeight.bold)),
              Slider(
                value: quantity.toDouble(),
                min: 4,
                max: 12,
                divisions: 2,
                label: '$quantity',
                onChanged: builderEnabled ? (value) => setState(() => quantity = value.round()) : null,
              ),
              TextField(
                controller: messageController,
                enabled: builderEnabled,
                maxLines: 3,
                decoration: InputDecoration(
                  labelText: 'Sticker messages (optional)',
                  hintText: 'เช่น สู้ ๆ นะ, ขอบคุณนะ, รักนะ',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
              const SizedBox(height: 20),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text('Preview: ${characterConfig.summary}', style: const TextStyle(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 6),
                      Text('$style • $theme • $quantity stickers'),
                      if (hasBackend && !isPollinationsConnected) ...[
                        const SizedBox(height: 8),
                        const Text('Connect Pollinations to unlock these controls.'),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Expanded(child: Text(status, style: const TextStyle(fontWeight: FontWeight.bold))),
                          Text('${(progress * 100).round()}%'),
                        ],
                      ),
                      const SizedBox(height: 10),
                      LinearProgressIndicator(value: progress),
                      if (errorMessage != null) ...[
                        const SizedBox(height: 10),
                        Text(errorMessage!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                      ],
                      if (showEarnPollenHint) ...[
                        const SizedBox(height: 10),
                        FilledButton.tonalIcon(
                          onPressed: _openEarnPollen,
                          icon: const Icon(Icons.task_alt),
                          label: const Text('Pollen not enough? Do Quests'),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                height: 52,
                child: ElevatedButton.icon(
                  onPressed: builderEnabled ? generateAssets : null,
                  icon: Icon(isGenerating ? Icons.hourglass_top : Icons.auto_awesome),
                  label: Text(isGenerating ? 'Generating...' : 'Generate Asset Pack'),
                ),
              ),
              if (generatedFiles.isNotEmpty) ...[
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text('Generated ${generatedFiles.length} files', style: const TextStyle(fontWeight: FontWeight.bold)),
                        const SizedBox(height: 8),
                        ...generatedFiles.take(6).map((name) => Text('• $name')),
                        const SizedBox(height: 12),
                        ElevatedButton.icon(
                          onPressed: isSaving || zipBase64 == null ? null : _saveAndShareZip,
                          icon: const Icon(Icons.download_rounded),
                          label: Text(isSaving ? 'Preparing ZIP...' : 'Download Asset Pack (.ZIP)'),
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
