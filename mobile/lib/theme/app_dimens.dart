import 'package:flutter/widgets.dart';

/// Espacements, rayons et épaisseurs partagés.
abstract final class AppDimens {
  static const double gap4 = 4;
  static const double gap8 = 8;
  static const double gap12 = 12;
  static const double gap16 = 16;
  static const double gap24 = 24;
  static const double gap32 = 32;
  static const double gap40 = 40;

  static const double pagePaddingH = 24;
  static const double maxContentWidth = 480;

  static const double radiusField = 14;
  static const double radiusButton = 14;

  static const double borderWidth = 1.6;
  static const double borderWidthStrong = 2.0;

  static const double buttonHeight = 56;

  static const EdgeInsets fieldContentPadding = EdgeInsets.symmetric(
    horizontal: 18,
    vertical: 18,
  );
}
