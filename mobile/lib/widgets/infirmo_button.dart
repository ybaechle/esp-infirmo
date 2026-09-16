import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../theme/app_typography.dart';

/// Variantes visuelles d'un [InfirmoButton].
enum InfirmoButtonVariant {
  /// Fond rouge plein, texte blanc (action principale).
  primary,

  /// Fond blanc, bordure noire, texte noir (action secondaire).
  secondary,
}

/// Bouton pleine largeur d'INFIRMO.
///
/// Gère l'état désactivé (grisé) et un état occupé qui remplace le libellé par
/// un indicateur de progression, sans changer la taille du bouton.
class InfirmoButton extends StatelessWidget {
  const InfirmoButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.variant = InfirmoButtonVariant.primary,
    this.busy = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final InfirmoButtonVariant variant;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final enabled = onPressed != null && !busy;
    final isPrimary = variant == InfirmoButtonVariant.primary;

    final Color fill;
    final Color foreground;
    final BorderSide side;

    if (isPrimary) {
      fill = enabled ? AppColors.red : AppColors.disabledFill;
      foreground = enabled ? AppColors.onRed : AppColors.disabledText;
      side = BorderSide.none;
    } else {
      fill = AppColors.surface;
      foreground = enabled ? AppColors.ink : AppColors.disabledText;
      side = BorderSide(
        color: enabled ? AppColors.ink : AppColors.disabledFill,
        width: AppDimens.borderWidthStrong,
      );
    }

    return SizedBox(
      height: AppDimens.buttonHeight,
      width: double.infinity,
      child: Material(
        color: fill,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDimens.radiusButton),
          side: side,
        ),
        child: InkWell(
          onTap: enabled ? onPressed : null,
          borderRadius: BorderRadius.circular(AppDimens.radiusButton),
          splashColor: isPrimary
              ? AppColors.redPressed.withValues(alpha: 0.4)
              : null,
          child: Center(
            child: busy
                ? SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      valueColor: AlwaysStoppedAnimation<Color>(foreground),
                    ),
                  )
                : Text(
                    label,
                    style: AppText.button.copyWith(color: foreground),
                    textAlign: TextAlign.center,
                  ),
          ),
        ),
      ),
    );
  }
}
