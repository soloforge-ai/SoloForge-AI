import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/pages/asset_forge_page.dart';

void main() {
  testWidgets('Asset Forge page renders the MVP controls', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: AssetForgePage(),
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
        home: AssetForgePage(),
      ),
    );

    await tester.tap(find.text('Generate Asset Pack'));
    await tester.pump();

    expect(find.text('Generating...'), findsOneWidget);

    // The simulated pipeline has 6 stages with a 600 ms delay each.
    // Advance beyond the full 3.6 second pipeline, then flush the
    // resulting microtasks so the final setState is rendered.
    await tester.pump(const Duration(seconds: 4));
    await tester.pump();

    expect(find.text('Asset Pack Ready!'), findsOneWidget);
    expect(find.text('Generate Asset Pack'), findsOneWidget);
  });
}
