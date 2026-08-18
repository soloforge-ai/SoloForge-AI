import 'package:flutter/material.dart';

/// SoloForge AI visual tokens — ASH (AI Signature Hybrid).
///
/// The palette is intentionally restrained: dark luxury first, color second.
/// Keep UI surfaces quiet and use Indigo/Oxblood only for hierarchy and action.
class AshColors {
  AshColors._();

  static const obsidian = Color(0xFF0D0C0F);
  static const blackPlum = Color(0xFF17131A);
  static const deepIndigo = Color(0xFF28345C);
  static const indigoMist = Color(0xFF596989);
  static const oxblood = Color(0xFF541C2A);
  static const velvetRed = Color(0xFF7A3042);
  static const smokeSilver = Color(0xFFA8ADB8);
  static const boneWhite = Color(0xFFE9E3DA);
  static const charcoal = Color(0xFF1A161C);
  static const mutedRose = Color(0xFF8A5963);
}

class SoloForgeTheme {
  SoloForgeTheme._();

  static ThemeData dark() {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AshColors.obsidian,
      canvasColor: AshColors.obsidian,
      cardColor: AshColors.charcoal,
      dividerColor: AshColors.indigoMist.withValues(alpha: 0.28),
      colorScheme: const ColorScheme.dark(
        primary: AshColors.deepIndigo,
        onPrimary: AshColors.boneWhite,
        secondary: AshColors.velvetRed,
        onSecondary: AshColors.boneWhite,
        surface: AshColors.charcoal,
        onSurface: AshColors.boneWhite,
        error: AshColors.velvetRed,
        onError: AshColors.boneWhite,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AshColors.obsidian,
        foregroundColor: AshColors.boneWhite,
        elevation: 0,
        centerTitle: false,
      ),
      cardTheme: CardThemeData(
        color: AshColors.charcoal,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(14)),
          side: BorderSide(color: AshColors.indigoMist, width: 0.45),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AshColors.blackPlum,
        hintStyle: const TextStyle(color: AshColors.smokeSilver),
        prefixIconColor: AshColors.indigoMist,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
          borderSide: BorderSide(color: AshColors.indigoMist, width: 0.6),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
          borderSide: BorderSide(color: AshColors.indigoMist, width: 0.6),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
          borderSide: BorderSide(color: AshColors.velvetRed, width: 1.2),
        ),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AshColors.deepIndigo,
      ),
      textTheme: const TextTheme(
        bodyLarge: TextStyle(color: AshColors.boneWhite),
        bodyMedium: TextStyle(color: AshColors.boneWhite),
        bodySmall: TextStyle(color: AshColors.smokeSilver),
      ),
    );
  }
}
