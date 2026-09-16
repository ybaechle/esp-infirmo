import 'package:flutter/widgets.dart';
import 'app_colors.dart';

/// Familles de polices embarquées (voir pubspec.yaml et assets/fonts/).
abstract final class AppFonts {
  static const String display = 'PermanentMarker';
  static const String sans = 'Archivo';

  /// Famille Google Fonts distincte (graisse unique 400), pour les gros titres.
  static const String black = 'ArchivoBlack';
}

/// Échelle typographique d'INFIRMO.
///
/// Tailles/graisses fournies par le design (Figma). Les styles marqués
/// « estimation » n'ont pas encore de valeur Figma confirmée.
abstract final class AppText {
  /// Logo « INFIRMO » — Permanent Marker 400, 42 px.
  static const TextStyle logo = TextStyle(
    fontFamily: AppFonts.display,
    fontWeight: FontWeight.w400,
    fontSize: 42,
    height: 1.0,
    color: AppColors.ink,
  );

  /// Accroche sous le logo — Archivo 700, 10 px, capitales.
  static const TextStyle tagline = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w700,
    fontSize: 10,
    height: 1.5,
    letterSpacing: 0.3,
    color: AppColors.ink,
  );

  /// Libellé de champ — Archivo 600, 12 px.
  static const TextStyle fieldLabel = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w600,
    fontSize: 12,
    height: 1.2,
    color: AppColors.ink,
  );

  /// Texte saisi dans un champ — Archivo 400, 14 px.
  static const TextStyle input = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w400,
    fontSize: 14,
    height: 1.3,
    color: AppColors.ink,
  );

  /// Indice/placeholder d'un champ — Archivo 400, 14 px, gris.
  static const TextStyle hint = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w400,
    fontSize: 14,
    height: 1.3,
    color: AppColors.textSecondary,
  );

  /// Libellé de bouton — Archivo 700, 15 px.
  static const TextStyle button = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w700,
    fontSize: 15,
    height: 1.2,
    letterSpacing: 0.5,
    color: AppColors.onRed,
  );

  /// Lien discret (« Mot de passe oublié ? ») — Archivo 600, 12 px, gris.
  static const TextStyle linkMuted = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w600,
    fontSize: 12,
    height: 1.2,
    color: AppColors.textSecondary,
  );

  /// Lien d'action teal — Archivo 600, 12 px.
  static const TextStyle linkAccent = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w600,
    fontSize: 12,
    height: 1.2,
    color: AppColors.accent,
  );

  /// Message d'erreur de validation — Archivo 600, 12 px, rouge (estimation).
  static const TextStyle error = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w600,
    fontSize: 12,
    height: 1.35,
    color: AppColors.error,
  );

  /// Titre d'écran (« Modifier mes informations ») — Archivo Black 400, 24 px.
  static const TextStyle pageTitle = TextStyle(
    fontFamily: AppFonts.black,
    fontWeight: FontWeight.w400,
    fontSize: 24,
    height: 1.1,
    color: AppColors.ink,
  );

  /// Sous-titre gris sous un titre d'écran — Archivo 400, 14 px (estimation).
  static const TextStyle pageSubtitle = TextStyle(
    fontFamily: AppFonts.sans,
    fontWeight: FontWeight.w400,
    fontSize: 14,
    height: 1.4,
    color: AppColors.textSecondary,
  );
}
