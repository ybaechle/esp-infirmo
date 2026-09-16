import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../theme/app_typography.dart';

/// Champ de saisie INFIRMO.
class InfirmoTextField extends StatelessWidget {
  const InfirmoTextField({
    super.key,
    required this.label,
    this.controller,
    this.hintText,
    this.trailing,
    this.obscureText = false,
    this.enabled = true,
    this.hasError = false,
    this.keyboardType,
    this.textInputAction,
    this.autocorrect = true,
    this.enableSuggestions = true,
    this.suffixIcon,
    this.validator,
    this.onFieldSubmitted,
    this.autofillHints,
  });

  final String label;
  final TextEditingController? controller;
  final String? hintText;
  final Widget? trailing;
  final bool obscureText;
  final bool enabled;
  final bool hasError;

  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final bool autocorrect;
  final bool enableSuggestions;
  final Widget? suffixIcon;
  final FormFieldValidator<String>? validator;
  final ValueChanged<String>? onFieldSubmitted;
  final Iterable<String>? autofillHints;

  OutlineInputBorder _border(Color color, double width) => OutlineInputBorder(
    borderRadius: BorderRadius.circular(AppDimens.radiusField),
    borderSide: BorderSide(color: color, width: width),
  );

  @override
  Widget build(BuildContext context) {
    final restColor = hasError ? AppColors.error : AppColors.ink;
    final restWidth = hasError
        ? AppDimens.borderWidthStrong
        : AppDimens.borderWidth;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: AppDimens.gap8),
          child: Row(
            children: [
              Expanded(child: Text(label, style: AppText.fieldLabel)),
              ?trailing,
            ],
          ),
        ),
        TextFormField(
          controller: controller,
          enabled: enabled,
          obscureText: obscureText,
          keyboardType: keyboardType,
          textInputAction: textInputAction,
          autocorrect: autocorrect,
          enableSuggestions: enableSuggestions,
          autofillHints: autofillHints,
          style: AppText.input,
          cursorColor: AppColors.ink,
          validator: validator,
          onFieldSubmitted: onFieldSubmitted,
          decoration: InputDecoration(
            isDense: false,
            filled: true,
            fillColor: AppColors.surface,
            hintText: hintText,
            hintStyle: AppText.hint,
            contentPadding: AppDimens.fieldContentPadding,
            suffixIcon: suffixIcon,
            errorStyle: AppText.error,
            errorMaxLines: 3,
            enabledBorder: _border(restColor, restWidth),
            focusedBorder: _border(
              hasError ? AppColors.error : AppColors.ink,
              AppDimens.borderWidthStrong,
            ),
            errorBorder: _border(AppColors.error, AppDimens.borderWidthStrong),
            focusedErrorBorder: _border(
              AppColors.error,
              AppDimens.borderWidthStrong,
            ),
            disabledBorder: _border(
              AppColors.textSecondary,
              AppDimens.borderWidth,
            ),
          ),
        ),
      ],
    );
  }
}
