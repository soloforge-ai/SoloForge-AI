import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../ai/content_engine.dart';
import '../ai/platforms.dart';
import '../ai/product_intelligence.dart';
import '../models/affiliate_product.dart';
import '../models/generated_content.dart';

import '../widgets/forge/analysis_card.dart';
import '../widgets/forge/content_studio.dart';
import '../widgets/forge/miniboss_card.dart';
import '../widgets/forge/product_assets_card.dart';
import '../widgets/forge/product_header.dart';
import '../widgets/forge/prompt_studio.dart';

class ForgePage extends StatefulWidget {
  final AffiliateProduct product;

  const ForgePage({
    super.key,
    required this.product,
  });

  @override
  State<ForgePage> createState() => _ForgePageState();
}

class _ForgePageState extends State<ForgePage> {
  int selectedPlatform = 0;

  final hookController = TextEditingController();
  final captionController = TextEditingController();
  final hashtagController = TextEditingController();
  final ctaController = TextEditingController();

  final platforms = const [
    PlatformType.facebook,
    PlatformType.tiktok,
    PlatformType.lemon8,
    PlatformType.x,
    PlatformType.youtube,
  ];

  bool isGenerating = false;

  late final ProductIntelligence intelligence;

  @override
  void initState() {
    super.initState();

    intelligence = const ProductIntelligenceEngine().analyze(
      widget.product.toProduct(),
    );
  }

  Future<void> generateContent() async {
    setState(() => isGenerating = true);

    try {
      final GeneratedContent content = await ContentEngine.generateContent(
        product: widget.product.toProduct(),
        platform: platforms[selectedPlatform],
      );

      if (!mounted) return;

      setState(() {
        hookController.text = content.hook;
        captionController.text = content.caption;
        hashtagController.text = content.hashtags.join(' ');
        ctaController.text = content.callToAction;
      });
    } finally {
      if (mounted) {
        setState(() => isGenerating = false);
      }
    }
  }

  void copyToClipboard(String text) {
    Clipboard.setData(
      ClipboardData(text: text),
    );

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Copied'),
      ),
    );
  }

  @override
  void dispose() {
    hookController.dispose();
    captionController.dispose();
    hashtagController.dispose();
    ctaController.dispose();

    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final product = widget.product;

    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Forge'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ProductHeader(product: product),

            const SizedBox(height: 20),

            MiniBossCard(product: product),

            const SizedBox(height: 20),

            AnalysisCard(
              intelligence: intelligence,
            ),

            const SizedBox(height: 20),

            ProductAssetsCard(product: product),

            const SizedBox(height: 20),

            PromptStudio(product: product),

            const SizedBox(height: 24),

            if (isGenerating)
              const Padding(
                padding: EdgeInsets.only(bottom: 16),
                child: LinearProgressIndicator(),
              ),

            ContentStudio(
              selectedPlatform: selectedPlatform,
              platforms: platforms,
              hookController: hookController,
              captionController: captionController,
              hashtagController: hashtagController,
              ctaController: ctaController,
              onPlatformChanged: (i) {
                setState(() {
                  selectedPlatform = i;
                });
              },
              onGenerate: generateContent,
              onCopy: () => copyToClipboard(
                '''
${hookController.text}

${captionController.text}

${hashtagController.text}

${ctaController.text}
''',
              ),
            ),
          ],
        ),
      ),
    );
  }
}