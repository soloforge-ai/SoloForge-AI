import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/pages/asset_forge_page.dart';
import 'package:frontend/pages/home_page.dart';

void main() {
  testWidgets('home sticker CTA opens authenticated Asset Forge', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: HomePage(),
      ),
    );

    await tester.pump();

    await tester.tap(find.text('สร้างสติ๊กเกอร์'));
    await tester.pumpAndSettle();

    expect(find.byType(AssetForgePage), findsOneWidget);
  });

  testWidgets('Pollen demo is locked to one four-sticker pack', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: AssetForgePage(useBackend: false),
      ),
    );

    expect(find.text('Demo pack: 4 stickers'), findsOneWidget);
    expect(find.byType(Slider), findsNothing);
  });
}
