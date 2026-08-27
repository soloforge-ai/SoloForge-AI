class AssetForgeCharacterConfig {
  const AssetForgeCharacterConfig({
    required this.characterType,
    required this.primaryColor,
  });

  final String characterType;
  final String primaryColor;

  static const soloForgeCharacters = {'CEO', 'Pearli', 'Aira'};

  String get backendCharacter {
    if (soloForgeCharacters.contains(characterType)) {
      return characterType;
    }
    return '$primaryColor $characterType mascot';
  }

  String get summary => '$primaryColor $characterType';
}
