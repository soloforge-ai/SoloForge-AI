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
}
