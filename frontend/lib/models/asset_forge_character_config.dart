class AssetForgeCharacterConfig {
  const AssetForgeCharacterConfig({
    required this.characterType,
    required this.primaryColor,
  });

  final String characterType;
  final String primaryColor;

  static const soloForgeCharacters = {'CEO', 'Pearli', 'Aira'};

  bool get isSoloForgeCharacter => soloForgeCharacters.contains(characterType);

  String get backendCharacter {
    if (isSoloForgeCharacter) {
      return characterType;
    }
    if (characterType == 'Human Mascot') {
      return '$primaryColor Human mascot';
    }
    return '$primaryColor $characterType mascot';
  }

  String get summary => isSoloForgeCharacter ? characterType : '$primaryColor $characterType';
}
