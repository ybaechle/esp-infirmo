import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../theme/app_typography.dart';

class InfirmoDropdownOption<T> {
  const InfirmoDropdownOption({required this.value, required this.label});
  final T value;
  final String label;
}

/// Sélecteur INFIRMO assorti à [InfirmoTextField].
class InfirmoDropdownField<T> extends StatelessWidget {
  const InfirmoDropdownField({
    super.key,
    required this.label,
    required this.value,
    required this.options,
    required this.onChanged,
    this.enabled = true,
  });

  final String label;
  final T value;
  final List<InfirmoDropdownOption<T>> options;
  final ValueChanged<T?>? onChanged;
  final bool enabled;

  OutlineInputBorder _border(Color color, double width) => OutlineInputBorder(
    borderRadius: BorderRadius.circular(AppDimens.radiusField),
    borderSide: BorderSide(color: color, width: width),
  );

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: AppDimens.gap8),
          child: Text(label, style: AppText.fieldLabel),
        ),
        DropdownButtonFormField<T>(
          key: ValueKey('$label-$value'),
          initialValue: value,
          isExpanded: true,
          style: AppText.input,
          icon: const Icon(Icons.keyboard_arrow_down_rounded),
          iconEnabledColor: AppColors.ink,
          dropdownColor: AppColors.surface,
          borderRadius: BorderRadius.circular(AppDimens.radiusField),
          onChanged: enabled ? onChanged : null,
          items: [
            for (final option in options)
              DropdownMenuItem<T>(
                value: option.value,
                child: Text(option.label, style: AppText.input),
              ),
          ],
          decoration: InputDecoration(
            filled: true,
            fillColor: AppColors.surface,
            contentPadding: AppDimens.fieldContentPadding,
            enabledBorder: _border(AppColors.ink, AppDimens.borderWidth),
            focusedBorder: _border(AppColors.ink, AppDimens.borderWidthStrong),
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
