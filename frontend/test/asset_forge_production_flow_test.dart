import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/pages/asset_forge_page.dart';

void main() {
  testWidgets('Asset Forge keeps the four-sticker V1 scope', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AssetForgePage(useBackend: false)),
    );

    expect(find.text('Demo pack: 4 stickers'), findsOneWidget);
    expect(find.text('Generate Asset Pack'), findsOneWidget);
    expect(find.byType(Slider), findsNothing);
  });
}
