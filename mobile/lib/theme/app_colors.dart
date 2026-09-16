import 'package:flutter/material.dart';

/// Palette centrale d'INFIRMO.
///
/// Source : maquettes Figma. Les valeurs ci-dessous sont des relevés à
/// confirmer avec les codes hexadécimaux exacts du fichier Figma. Toute
/// l'application référence ces jetons : ajuster ici se propage partout.
abstract final class AppColors {
  /// Fond crème des écrans.
  static const Color background = Color(0xFFF6F1E6);

  /// Remplissage blanc des champs et boutons secondaires.
  static const Color surface = Color(0xFFFFFFFF);

  /// Rouge principal : bouton primaire, bordures et messages d'erreur.
  static const Color red = Color(0xFFEF4B45);

  /// Rouge pressé (états d'appui du bouton primaire).
  static const Color redPressed = Color(0xFFD83E39);

  /// Erreur : même rouge que la marque (bordure + texte de validation).
  static const Color error = red;

  /// Teal/vert des liens d'action (ex. « Où trouver mon numéro ? »).
  static const Color accent = Color(0xFF0C7B69);

  /// Jaune du surlignage sous le logo INFIRMO.
  static const Color highlight = Color(0xFFF6C445);

  /// Noir « encre » : titres, libellés, texte saisi, bordures au repos.
  static const Color ink = Color(0xFF141414);

  /// Gris secondaire : liens discrets, indices de saisie, notes de pied.
  static const Color textSecondary = Color(0xFF9E9A92);

  /// Remplissage d'un bouton primaire désactivé.
  static const Color disabledFill = Color(0xFFD3CFC7);

  /// Texte d'un bouton primaire désactivé.
  static const Color disabledText = Color(0xFF8B877E);

  /// Texte posé sur le rouge principal.
  static const Color onRed = Color(0xFFFFFFFF);
}
