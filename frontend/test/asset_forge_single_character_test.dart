import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/asset_forge_generation_config.dart';
import 'package:frontend/pages/asset_forge_page.dart';

void main() {
  test('single API request uses exactly one pose and expression', () {
    const config = AssetForgeGenerationConfig(layout: 'single_character');
    expect(config.requestFields([]), {
      'generation_layout': 'single_character', 'quantity': 1, 'messages': [],
      'wardrobe_variant': 'default', 'campaign_id': null,
      'pose_intent': 'presenting', 'expression': 'calm', 'framing': 'full_figure',
    });
    expect(() => config.requestFields(['Presenting', 'Pointing']), throwsArgumentError);
    expect(() => const AssetForgeGenerationConfig(layout: 'single_character',
      pose: 'thinking', expression: 'subtle_smile').requestFields([]), throwsArgumentError);
  });

  test('legacy sheets retain four poses and old response compatibility', () {
    const config = AssetForgeGenerationConfig();
    expect(config.requestFields(['Hello'])['quantity'], 4);
    expect(config.requestFields([]).containsKey('pose_intent'), isFalse);
    config.validateResponse({'files': ['a', 'b', 'c', 'd']});
  });

  test('single response rejects fallback or a four-cell pack', () {
    const config = AssetForgeGenerationConfig(layout: 'single_character');
    final valid = {'generation_layout': 'single_character', 'generation_mode': 'pollinations',
      'source_image_base64': 'fixture-image-data',
      'files': ['01_ceo_single.png'], 'output_manifest': {'generation_layout': 'single_character', 'quantity': 1}};
    config.validateResponse(valid);
    expect(() => config.validateResponse({...valid, 'generation_mode': 'local_fallback'}), throwsStateError);
    expect(() => config.validateResponse({...valid, 'files': ['a', 'b', 'c', 'd']}), throwsStateError);
  });

  testWidgets('CEO single UI offers one intent without sticker messages', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: AssetForgePage(useBackend: false)));
    final character = find.byType(DropdownButtonFormField<String>).first;
    await tester.tap(character);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('CEO').last);
    await tester.tap(find.text('CEO').last);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Generation mode'));
    await tester.tap(find.text('Sticker pack'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Single CEO image').last);
    await tester.pumpAndSettle();
    expect(find.text('One pose'), findsOneWidget);
    expect(find.text('One expression'), findsOneWidget);
    expect(find.text('Sticker messages (optional)'), findsNothing);
    expect(find.text('Single image: 1 CEO character'), findsOneWidget);
    await tester.ensureVisible(find.text('Generate Single CEO Image'));
    await tester.tap(find.text('Generate Single CEO Image'));
    await tester.pumpAndSettle();
    expect(find.textContaining('No local fallback.'), findsWidgets);
    expect(find.byKey(const Key('manual-fix-card')), findsNothing);
  });
}
