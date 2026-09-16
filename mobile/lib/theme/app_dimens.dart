import 'package:flutter/widgets.dart';

/// Espacements, rayons et épaisseurs partagés.
///
/// Rayons/épaisseurs relevés sur les maquettes (à ajuster si Figma diffère).
abstract final class AppDimens {
  // Espacements verticaux/horizontaux (échelle de 4).
  static const double gap4 = 4;
  static const double gap8 = 8;
  static const double gap12 = 12;
  static const double gap16 = 16;
  static const double gap24 = 24;
  static const double gap32 = 32;
  static const double gap40 = 40;

  /// Marge horizontale des écrans.
  static const double pagePaddingH = 24;

  /// Largeur de contenu maximale (tablette/desktop web).
  static const double maxContentWidth = 480;

  /// Rayon des champs de saisie.
  static const double radiusField = 14;

  /// Rayon des boutons.
  static const double radiusButton = 14;

  /// Épaisseur de bordure d'un champ au repos.
  static const double borderWidth = 1.6;

  /// Épaisseur de bordure d'un champ en erreur / focus.
  static const double borderWidthStrong = 2.0;

  /// Hauteur minimale des boutons.
  static const double buttonHeight = 56;

  /// Rembourrage interne des champs.
  static const EdgeInsets fieldContentPadding = EdgeInsets.symmetric(
    horizontal: 18,
    vertical: 18,
  );
}
