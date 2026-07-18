enum PlatformType {
  tiktok,
  facebook,
  instagram,
  lemon8,
  youtube,
  x,
}

extension PlatformTypeExtension on PlatformType {
  String get displayName {
    switch (this) {
      case PlatformType.tiktok:
        return 'TikTok';

      case PlatformType.facebook:
        return 'Facebook';

      case PlatformType.instagram:
        return 'Instagram';

      case PlatformType.lemon8:
        return 'Lemon8';

      case PlatformType.youtube:
        return 'YouTube Shorts';

      case PlatformType.x:
        return 'X';
    }
  }
}