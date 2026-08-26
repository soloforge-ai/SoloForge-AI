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
}
