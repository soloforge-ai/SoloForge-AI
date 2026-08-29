class AssetForgeCharacterConfig {
  const AssetForgeCharacterConfig({
    required this.characterType,
    required this.primaryColor,
  });

  final String characterType;
  final String primaryColor;

  static const soloForgeCharacters = {'CEO', 'Pearli', 'Aira'};

  static bool isPollenPaymentFailure({
    required int statusCode,
    required String message,
  }) {
    final normalized = message.toLowerCase();
    return statusCode == 402 ||
        normalized.contains('failed (402)') ||
        normalized.contains('payment required') ||
        normalized.contains('pollen') ||
        normalized.contains('balance') ||
        normalized.contains('credit');
  }

  bool get isSoloForgeCharacter => soloForgeCharacters.contains(characterType);

  String get backendCharacter {
    if (isSoloForgeCharacter) {
      return characterType;
    }
    if (characterType == 'Human Male') {
      return '$primaryColor male human chibi mascot';
    }
    if (characterType == 'Human Female') {
      return '$primaryColor female human chibi mascot';
    }
    return '$primaryColor $characterType chibi mascot';
  }

  String get summary => isSoloForgeCharacter ? characterType : '$primaryColor $characterType';
}
