import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_typography.dart';

/// Message d'erreur ou de confirmation au niveau du formulaire.
class FormMessage extends StatelessWidget {
  const FormMessage({super.key, required this.text, this.isError = true});

  final String text;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Text(
        text,
        style: AppText.error.copyWith(
          color: isError ? AppColors.error : AppColors.accent,
        ),
      ),
    );
  }
}
