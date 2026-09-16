import 'package:flutter/widgets.dart';
import 'app_colors.dart';

/// Familles de polices embarquées.
abstract final class AppFonts {
  static const String display = 'PermanentMarker';
  static const String sans = 'Archivo';
  static const String black = 'ArchivoBlack';
}

/// Échelle typographique d'INFIRMO.
abstract final class AppText {
  static const TextStyle logo = TextStyle(
    fontFamily: AppFonts.display,
    fontWeight: FontWeight.w400,
    fontSize: 42,
    height: 1.0,
    color: AppColors.ink,
  );

  static const TextStyle tagline = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w700,
    fontSize: 10,
    height: 1.5,
    letterSpacing: 0.3,
    color: AppColors.ink,
  );

  static const TextStyle fieldLabel = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w600,
    fontSize: 12,
    height: 1.2,
    color: AppColors.ink,
  );

  static const TextStyle input = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w400,
    fontSize: 14,
    height: 1.3,
    color: AppColors.ink,
  );

  static const TextStyle hint = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w400,
    fontSize: 14,
    height: 1.3,
    color: AppColors.textSecondary,
  );

  static const TextStyle button = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w700,
    fontSize: 15,
    height: 1.2,
    letterSpacing: 0.5,
    color: AppColors.onRed,
  );

  static const TextStyle linkMuted = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w600,
    fontSize: 12,
    height: 1.2,
    color: AppColors.textSecondary,
  );

  static const TextStyle linkAccent = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w600,
    fontSize: 12,
    height: 1.2,
    color: AppColors.accent,
  );

  static const TextStyle error = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w600,
    fontSize: 12,
    height: 1.35,
    color: AppColors.error,
  );

  static const TextStyle pageTitle = TextStyle(
    fontFamily: AppFonts.black,
    fontWeight: FontWeight.w400,
    fontSize: 24,
    height: 1.1,
    color: AppColors.ink,
  );

  static const TextStyle pageSubtitle = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w400,
    fontSize: 14,
    height: 1.4,
    color: AppColors.textSecondary,
  );
}
