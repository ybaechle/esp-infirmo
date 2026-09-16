import 'package:flutter/material.dart';
import 'app_colors.dart';
import 'app_typography.dart';

/// Thème Material dérivé des jetons INFIRMO.
///
/// Les composants du dossier `widgets/` portent le rendu fidèle aux maquettes ;
/// ce thème fixe les valeurs par défaut (police, fond, sélection de texte).
abstract final class AppTheme {
  static ThemeData get light {
    final scheme =
        ColorScheme.fromSeed(
          seedColor: AppColors.accent,
          brightness: Brightness.light,
        ).copyWith(
          primary: AppColors.red,
          error: AppColors.error,
          surface: AppColors.background,
        );

    return ThemeData(
      useMaterial3: true,
      fontFamily: AppFonts.sans,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.background,
      textSelectionTheme: const TextSelectionThemeData(
        cursorColor: AppColors.ink,
        selectionHandleColor: AppColors.accent,
      ),
      splashFactory: InkRipple.splashFactory,
    );
  }
}
