import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_typography.dart';

/// Message textuel au niveau du formulaire (erreur globale ou confirmation),
/// annoncé aux lecteurs d'écran via une région « live ».
///
/// Exemple : « E-mail ou mot de passe incorrect. » sous les champs de connexion.
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
