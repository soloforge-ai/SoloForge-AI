
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../models/affiliate_product.dart';
import '../../services/prompt_engine/prompt_context.dart';
import '../../services/prompt_engine/image_prompt_service.dart';
import '../../services/prompt_engine/video_prompt_service.dart';
import '../../services/prompt_engine/voice_prompt_service.dart';
import 'content_field.dart';

class PromptStudio extends StatefulWidget {
  final AffiliateProduct product;

  const PromptStudio({
    super.key,
    required this.product,
  });

  @override
  State<PromptStudio> createState() => _PromptStudioState();
}

class _PromptStudioState extends State<PromptStudio> {
  final _imageController = TextEditingController();
  final _videoController = TextEditingController();
  final _voiceController = TextEditingController();

  final _imageService = const ImagePromptService();
  final _videoService = const VideoPromptService();
  final _voiceService = const VoicePromptService();

  void _generateAll() {
    final context = PromptContext(product: widget.product);

    setState(() {
      _imageController.text =
          _imageService.buildProductPrompt(context);
      _videoController.text =
          _videoService.buildProductVideoPrompt(context);
      _voiceController.text =
          _voiceService.buildNarrationPrompt(context);
    });
  }

  void _copy(String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Copied'),
        duration: Duration(seconds: 1),
      ),
    );
  }

  @override
  void dispose() {
    _imageController.dispose();
    _videoController.dispose();
    _voiceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'AI Prompt Studio',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _generateAll,
              icon: const Icon(Icons.auto_awesome),
              label: const Text('Generate All Prompts'),
            ),
            const SizedBox(height: 20),
            ContentField(
              label: 'Image Prompt',
              hint: 'Generate image prompt...',
              controller: _imageController,
              maxLines: 10,
              readOnly: true,
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () => _copy(_imageController.text),
                child: const Text('Copy'),
              ),
            ),
            ContentField(
              label: 'Video Prompt',
              hint: 'Generate video prompt...',
              controller: _videoController,
              maxLines: 10,
              readOnly: true,
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () => _copy(_videoController.text),
                child: const Text('Copy'),
              ),
            ),
            ContentField(
              label: 'Voice Prompt',
              hint: 'Generate voice prompt...',
              controller: _voiceController,
              maxLines: 10,
              readOnly: true,
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () => _copy(_voiceController.text),
                child: const Text('Copy'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
