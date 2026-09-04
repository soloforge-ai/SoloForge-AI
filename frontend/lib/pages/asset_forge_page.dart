import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:archive/archive.dart';
import 'package:file_picker/file_picker.dart';
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
  static const String style = 'Cute 3D Chibi';

  String characterType = 'Cat';
  String primaryColor = 'Blue';
  String product = 'Sticker';
  String theme = 'Healing & Encouragement';
  int quantity = 4;

  bool isGenerating = false;
  bool isSaving = false;
  bool isPreparingReview = false;
  bool isPreparingCrops = false;
  bool isConnectingPollinations = false;
  bool isPollinationsConnected = false;
  bool showEarnPollenHint = false;
  double progress = 0.0;
  String status = 'Ready';
  String pollinationsStatus = 'Not connected';
  String? errorMessage;
  List<String> generatedFiles = const [];
  String? zipBase64;
  Uint8List? previewBytes;
  List<Uint8List> quickReviewBytes = const [];
  Uint8List? cleanedSheetBytes;
  List<Uint8List> croppedStickerBytes = const [];
  double verticalSplit = 0.5;
  double horizontalSplit = 0.5;

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

  Future<Uint8List> _cropPng(ui.Image source, Rect sourceRect) async {
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);
    final outputWidth = sourceRect.width.round();
    final outputHeight = sourceRect.height.round();
    canvas.drawImageRect(
      source,
      sourceRect,
      Rect.fromLTWH(0, 0, outputWidth.toDouble(), outputHeight.toDouble()),
      Paint(),
    );
    final image = await recorder.endRecording().toImage(outputWidth, outputHeight);
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    image.dispose();
    if (data == null) throw Exception('แปลงภาพ PNG ไม่สำเร็จ');
    return data.buffer.asUint8List();
  }

  Future<Uint8List> _encodePng(Uint8List bytes) async {
    final codec = await ui.instantiateImageCodec(bytes);
    final frame = await codec.getNextFrame();
    final image = frame.image;
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    image.dispose();
    codec.dispose();
    if (data == null) throw Exception('แปลงภาพ PNG ไม่สำเร็จ');
    return data.buffer.asUint8List();
  }

  Future<List<Uint8List>> _splitTwoByTwo(
    Uint8List bytes, {
    required double splitXRatio,
    required double splitYRatio,
  }) async {
    final codec = await ui.instantiateImageCodec(bytes);
    final frame = await codec.getNextFrame();
    final image = frame.image;
    final width = image.width.toDouble();
    final height = image.height.toDouble();
    final splitX = (width * splitXRatio).roundToDouble().clamp(1, width - 1).toDouble();
    final splitY = (height * splitYRatio).roundToDouble().clamp(1, height - 1).toDouble();
    final rects = <Rect>[
      Rect.fromLTRB(0, 0, splitX, splitY),
      Rect.fromLTRB(splitX, 0, width, splitY),
      Rect.fromLTRB(0, splitY, splitX, height),
      Rect.fromLTRB(splitX, splitY, width, height),
    ];
    final crops = <Uint8List>[];
    for (final rect in rects) {
      crops.add(await _cropPng(image, rect));
    }
    image.dispose();
    codec.dispose();
    return crops;
  }

  Future<void> _prepareQuickReview(Uint8List bytes) async {
    if (isPreparingReview) return;
    setState(() {
      isPreparingReview = true;
      quickReviewBytes = const [];
    });
    try {
      final crops = await _splitTwoByTwo(
        bytes,
        splitXRatio: 0.5,
        splitYRatio: 0.5,
      );
      if (mounted) setState(() => quickReviewBytes = crops);
    } catch (error) {
      if (mounted) {
        setState(() => errorMessage = 'เตรียมตัวอย่าง 4 แบบไม่สำเร็จ: $error');
      }
    } finally {
      if (mounted) setState(() => isPreparingReview = false);
    }
  }

  Future<void> _shareGeneratedSheet() async {
    final source = previewBytes;
    if (source == null || isSaving) return;
    setState(() {
      isSaving = true;
      errorMessage = null;
    });
    try {
      final pngBytes = await _encodePng(source);
      final directory = await getTemporaryDirectory();
      final file = File('${directory.path}/soloforge_sticker_sheet.png');
      await file.writeAsBytes(pngBytes, flush: true);
      await SharePlus.instance.share(
        ShareParams(
          files: [XFile(file.path)],
          title: 'SoloForge Sticker Sheet',
          text: 'Original 2×2 sheet for optional manual cleanup.',
        ),
      );
    } catch (error) {
      if (mounted) setState(() => errorMessage = 'บันทึกชีตไม่สำเร็จ: $error');
    } finally {
      if (mounted) setState(() => isSaving = false);
    }
  }

  Future<void> _pickCleanedSheet() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.image,
        allowMultiple: false,
        withData: true,
      );
      if (result == null) return;
      final picked = result.files.single;
      final bytes = picked.bytes ?? (picked.path == null ? null : await File(picked.path!).readAsBytes());
      if (bytes == null || bytes.isEmpty) throw Exception('ไม่พบข้อมูลรูปภาพ');
      setState(() {
        cleanedSheetBytes = bytes;
        croppedStickerBytes = const [];
        verticalSplit = 0.5;
        horizontalSplit = 0.5;
        errorMessage = null;
      });
      await _prepareCrops();
    } catch (error) {
      if (mounted) {
        setState(() {
          croppedStickerBytes = const [];
          errorMessage = 'อัปโหลดภาพไม่สำเร็จ: $error';
        });
      }
    }
  }

  Future<void> _prepareCrops() async {
    final bytes = cleanedSheetBytes;
    if (bytes == null || isPreparingCrops) return;
    setState(() => isPreparingCrops = true);
    try {
      final crops = await _splitTwoByTwo(
        bytes,
        splitXRatio: verticalSplit,
        splitYRatio: horizontalSplit,
      );
      if (mounted) setState(() => croppedStickerBytes = crops);
    } catch (error) {
      if (mounted) {
        setState(() {
          croppedStickerBytes = const [];
          errorMessage = 'ตัดภาพไม่สำเร็จ: $error';
        });
      }
    } finally {
      if (mounted) setState(() => isPreparingCrops = false);
    }
  }

  Future<void> _shareCrop(int index) async {
    if (index >= croppedStickerBytes.length || isSaving) return;
    setState(() => isSaving = true);
    try {
      final directory = await getTemporaryDirectory();
      final file = File('${directory.path}/soloforge_sticker_${index + 1}.png');
      await file.writeAsBytes(croppedStickerBytes[index], flush: true);
      await SharePlus.instance.share(ShareParams(files: [XFile(file.path)]));
    } catch (error) {
      if (mounted) setState(() => errorMessage = 'บันทึกสติกเกอร์ไม่สำเร็จ: $error');
    } finally {
      if (mounted) setState(() => isSaving = false);
    }
  }

  Future<void> _shareCroppedZip() async {
    if (croppedStickerBytes.length != 4 || isSaving) return;
    setState(() => isSaving = true);
    try {
      final archive = Archive();
      for (var index = 0; index < croppedStickerBytes.length; index++) {
        final bytes = croppedStickerBytes[index];
        archive.addFile(ArchiveFile('sticker_${index + 1}.png', bytes.length, bytes));
      }
      final zip = ZipEncoder().encode(archive);
      final directory = await getTemporaryDirectory();
      final file = File('${directory.path}/soloforge_4_stickers_fixed.zip');
      await file.writeAsBytes(zip, flush: true);
      await SharePlus.instance.share(
        ShareParams(files: [XFile(file.path)], title: 'SoloForge 4 Sticker Pack'),
      );
    } catch (error) {
      if (mounted) setState(() => errorMessage = 'สร้าง ZIP ไม่สำเร็จ: $error');
    } finally {
      if (mounted) setState(() => isSaving = false);
    }
  }

  Future<void> _simulatePipeline() async {
    for (final step in <String>[
      'Preparing prompt...',
      'Generating 4-pose sheet...',
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
      generatedFiles = List.generate(
        quantity,
        (index) => '${(index + 1).toString().padLeft(2, '0')}_beta_sticker.png',
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
    final files = (body['files'] as List<dynamic>? ?? const [])
        .map((value) => value.toString())
        .toList();
    final sourceImage = body['source_image_base64']?.toString();
    final sourceBytes = sourceImage == null || sourceImage.isEmpty
        ? null
        : base64Decode(sourceImage);

    if (!mounted) return;
    setState(() {
      progress = 1.0;
      generatedFiles = files;
      zipBase64 = body['zip_base64']?.toString();
      previewBytes = sourceBytes;
      status = 'Asset Pack Ready!';
      isGenerating = false;
      showEarnPollenHint = false;
    });

    if (sourceBytes != null) {
      await _prepareQuickReview(sourceBytes);
    }
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
      status = hasBackend ? 'Starting one-call 4-pose generation...' : 'Preparing...';
      errorMessage = null;
      generatedFiles = const [];
      zipBase64 = null;
      previewBytes = null;
      quickReviewBytes = const [];
      cleanedSheetBytes = null;
      croppedStickerBytes = const [];
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
      final safeCharacter = characterConfig.backendCharacter
          .toLowerCase()
          .replaceAll(RegExp(r'[^a-z0-9]+'), '_');
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
      decoration: InputDecoration(
        labelText: label,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      ),
      items: items
          .map((item) => DropdownMenuItem(value: item, child: Text(item)))
          .toList(),
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
                const Expanded(
                  child: Text('Pollinations', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
                Text(pollinationsStatus),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              connected
                  ? 'Connected. One generation creates the four-pose Quick Pack.'
                  : 'Connect Pollinations first. Character Builder unlocks after authorization.',
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

  Widget _buildPoseGrid(List<Uint8List> poses) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
      ),
      itemCount: poses.length,
      itemBuilder: (context, index) => Stack(
        fit: StackFit.expand,
        children: [
          DecoratedBox(
            decoration: BoxDecoration(
              border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Padding(
              padding: const EdgeInsets.all(6),
              child: Image.memory(poses[index], fit: BoxFit.contain),
            ),
          ),
          Align(
            alignment: Alignment.topLeft,
            child: Padding(
              padding: const EdgeInsets.all(6),
              child: CircleAvatar(
                radius: 14,
                child: Text('${index + 1}'),
              ),
            ),
          ),
        ],
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
                      Text(
                        'SoloForge Asset Forge Beta',
                        style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                      ),
                      SizedBox(height: 6),
                      Text('Generate 4 poses once → Review → Export'),
                    ],
                  ),
                ),
              ),
              if (hasBackend) ...[
                const SizedBox(height: 12),
                _buildPollinationsCard(),
              ],
              const SizedBox(height: 20),
              Text(
                'Character Builder',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              _dropdown(
                label: 'Character type',
                value: characterType,
                items: const [
                  'Cat',
                  'Dog',
                  'Bear',
                  'Rabbit',
                  'Robot',
                  'Human Male',
                  'Human Female',
                  'CEO',
                  'Pearli',
                  'Aira',
                ],
                onChanged: (value) {
                  if (value != null) setState(() => characterType = value);
                },
              ),
              const SizedBox(height: 12),
              _dropdown(
                label: 'Primary color',
                value: primaryColor,
                items: const [
                  'Blue',
                  'Black',
                  'White',
                  'Pink',
                  'Red',
                  'Green',
                  'Purple',
                  'Yellow',
                ],
                onChanged: (value) {
                  if (value != null) setState(() => primaryColor = value);
                },
              ),
              const SizedBox(height: 12),
              _dropdown(
                label: 'Theme',
                value: theme,
                items: const [
                  'Healing & Encouragement',
                  'Love',
                  'Abundance',
                  'Good Morning',
                ],
                onChanged: (value) {
                  if (value != null) setState(() => theme = value);
                },
              ),
              const SizedBox(height: 12),
              const Text('Style: Cute 3D Chibi', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 16),
              const Text('Demo pack: 4 stickers', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              const Text('Quick Pack uses one AI generation for all four poses.'),
              const SizedBox(height: 10),
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
                      Text(
                        'Preview: ${characterConfig.summary}',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
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
                          Expanded(
                            child: Text(status, style: const TextStyle(fontWeight: FontWeight.bold)),
                          ),
                          Text('${(progress * 100).round()}%'),
                        ],
                      ),
                      const SizedBox(height: 10),
                      LinearProgressIndicator(value: progress),
                      if (errorMessage != null) ...[
                        const SizedBox(height: 10),
                        Text(
                          errorMessage!,
                          style: TextStyle(color: Theme.of(context).colorScheme.error),
                        ),
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
              if (previewBytes != null) ...[
                const SizedBox(height: 16),
                Card(
                  key: const Key('quick-pack-review'),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          'Quick Pack Review',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Four poses from one AI generation. If they look good, export the automatic pack now.',
                        ),
                        const SizedBox(height: 12),
                        if (isPreparingReview)
                          const LinearProgressIndicator()
                        else if (quickReviewBytes.length == 4)
                          _buildPoseGrid(quickReviewBytes)
                        else
                          ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: Image.memory(previewBytes!, fit: BoxFit.contain),
                          ),
                        const SizedBox(height: 12),
                        FilledButton.icon(
                          key: const Key('download-automatic-pack'),
                          onPressed: isSaving || zipBase64 == null ? null : _saveAndShareZip,
                          icon: const Icon(Icons.folder_zip),
                          label: Text(
                            isSaving ? 'Preparing ZIP...' : 'Download automatic pack (.ZIP)',
                          ),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'No extra AI call is used for review or export.',
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  key: const Key('manual-fix-card'),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          'Need a cleanup?',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Optional fallback only. Keep the Quick Pack if it is already good. For a problem sheet, clean the 2×2 image in any tool you trust, then import it back here. This uses 0 additional Pollen.',
                        ),
                        const SizedBox(height: 10),
                        OutlinedButton.icon(
                          key: const Key('share-original-sheet'),
                          onPressed: isSaving ? null : _shareGeneratedSheet,
                          icon: const Icon(Icons.share_outlined),
                          label: const Text('Share original 2×2 sheet'),
                        ),
                        FilledButton.tonalIcon(
                          key: const Key('upload-cleaned-sheet'),
                          onPressed: _pickCleanedSheet,
                          icon: const Icon(Icons.upload_file),
                          label: const Text('Import cleaned 2×2 PNG'),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              if (cleanedSheetBytes != null) ...[
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          'Manual fix: adjust the 2×2 split',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 10),
                        CustomPaint(
                          foregroundPainter: _GridSplitPainter(
                            verticalSplit: verticalSplit,
                            horizontalSplit: horizontalSplit,
                          ),
                          child: Image.memory(
                            cleanedSheetBytes!,
                            fit: BoxFit.contain,
                            gaplessPlayback: true,
                          ),
                        ),
                        Text('Vertical split ${(verticalSplit * 100).round()}%'),
                        Slider(
                          key: const Key('vertical-grid-slider'),
                          value: verticalSplit,
                          min: 0.35,
                          max: 0.65,
                          onChanged: isPreparingCrops
                              ? null
                              : (value) => setState(() => verticalSplit = value),
                          onChangeEnd: (_) => _prepareCrops(),
                        ),
                        Text('Horizontal split ${(horizontalSplit * 100).round()}%'),
                        Slider(
                          key: const Key('horizontal-grid-slider'),
                          value: horizontalSplit,
                          min: 0.35,
                          max: 0.65,
                          onChanged: isPreparingCrops
                              ? null
                              : (value) => setState(() => horizontalSplit = value),
                          onChangeEnd: (_) => _prepareCrops(),
                        ),
                        if (isPreparingCrops) const LinearProgressIndicator(),
                      ],
                    ),
                  ),
                ),
              ],
              if (croppedStickerBytes.length == 4) ...[
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          'Manual fix previews',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 12),
                        GridView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 2,
                            crossAxisSpacing: 10,
                            mainAxisSpacing: 10,
                          ),
                          itemCount: 4,
                          itemBuilder: (context, index) => InkWell(
                            onTap: isSaving ? null : () => _shareCrop(index),
                            child: Stack(
                              fit: StackFit.expand,
                              children: [
                                Image.memory(croppedStickerBytes[index], fit: BoxFit.contain),
                                const Align(
                                  alignment: Alignment.bottomRight,
                                  child: Padding(
                                    padding: EdgeInsets.all(6),
                                    child: Icon(Icons.download_rounded),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        FilledButton.icon(
                          key: const Key('download-cropped-zip'),
                          onPressed: isSaving ? null : _shareCroppedZip,
                          icon: const Icon(Icons.folder_zip),
                          label: Text(
                            isSaving ? 'กำลังเตรียมไฟล์...' : 'Download fixed pack (.ZIP)',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              if (generatedFiles.isNotEmpty && previewBytes == null) ...[
                const SizedBox(height: 16),
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
                        ...generatedFiles.take(6).map((name) => Text('• $name')),
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

class _GridSplitPainter extends CustomPainter {
  const _GridSplitPainter({
    required this.verticalSplit,
    required this.horizontalSplit,
  });

  final double verticalSplit;
  final double horizontalSplit;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.redAccent
      ..strokeWidth = 2.5;
    canvas.drawLine(
      Offset(size.width * verticalSplit, 0),
      Offset(size.width * verticalSplit, size.height),
      paint,
    );
    canvas.drawLine(
      Offset(0, size.height * horizontalSplit),
      Offset(size.width, size.height * horizontalSplit),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant _GridSplitPainter oldDelegate) {
    return verticalSplit != oldDelegate.verticalSplit ||
        horizontalSplit != oldDelegate.horizontalSplit;
  }
}
