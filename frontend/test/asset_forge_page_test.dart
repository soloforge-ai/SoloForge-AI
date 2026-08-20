import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/pages/asset_forge_page.dart';

void main() {
  testWidgets('Asset Forge page renders the MVP controls', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: AssetForgePage(useBackend: false),
      ),
    );

    expect(find.text('SoloForge Asset Forge'), findsOneWidget);
    expect(find.text('Generate Asset Pack'), findsOneWidget);
    expect(find.text('Character'), findsOneWidget);
    expect(find.text('Product'), findsOneWidget);
    expect(find.text('Theme'), findsOneWidget);
    expect(find.text('Style'), findsOneWidget);
  });

  testWidgets('Generate Asset Pack completes the simulated pipeline', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        // Widget tests must not make a real HTTP request or invoke native OAuth
        // plugins. Production still uses the real Render backend because
        // useBackend defaults to the configured ASSET_FORGE_API_URL.
        home: AssetForgePage(useBackend: false),
      ),
    );

    final generateButton = find.text('Generate Asset Pack');
    await tester.ensureVisible(generateButton);
    await tester.pumpAndSettle();
    await tester.tap(generateButton);
    await tester.pump();

    expect(find.text('Generating...'), findsOneWidget);

    for (int i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 600));
    }
    await tester.pump();

    expect(find.text('Asset Pack Ready!'), findsOneWidget);
    expect(find.text('Generate Asset Pack'), findsOneWidget);
  });
}
