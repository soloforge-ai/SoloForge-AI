import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/asset_forge_character_config.dart';

void main() {
  test('custom character includes primary color in backend character', () {
    const config = AssetForgeCharacterConfig(
      characterType: 'Cat',
      primaryColor: 'Blue',
    );

    expect(config.backendCharacter, 'Blue Cat mascot');
    expect(config.summary, 'Blue Cat');
  });

  test('human mascot does not duplicate mascot in backend character', () {
    const config = AssetForgeCharacterConfig(
      characterType: 'Human Mascot',
      primaryColor: 'Blue',
    );

    expect(config.backendCharacter, 'Blue Human mascot');
    expect(config.summary, 'Blue Human Mascot');
  });

  test('SoloForge character keeps canonical identity and summary', () {
    const config = AssetForgeCharacterConfig(
      characterType: 'CEO',
      primaryColor: 'Pink',
    );

    expect(config.backendCharacter, 'CEO');
    expect(config.summary, 'CEO');
  });

  test('upstream Pollinations 402 wrapped by backend still shows Pollen CTA', () {
    expect(
      AssetForgeCharacterConfig.isPollenPaymentFailure(
        statusCode: 502,
        message: 'Pollinations image generation failed (402): Payment Required',
      ),
      isTrue,
    );
  });

  test('direct 402 shows Pollen CTA', () {
    expect(
      AssetForgeCharacterConfig.isPollenPaymentFailure(
        statusCode: 402,
        message: 'Asset Forge server returned 402.',
      ),
      isTrue,
    );
  });

  test('unrelated server error does not show Pollen CTA', () {
    expect(
      AssetForgeCharacterConfig.isPollenPaymentFailure(
        statusCode: 500,
        message: 'Internal server error',
      ),
      isFalse,
    );
  });
}
