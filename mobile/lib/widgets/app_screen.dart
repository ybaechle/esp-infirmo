import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';

/// Ossature commune d'un écran INFIRMO.
class AppScreen extends StatelessWidget {
  const AppScreen({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsets? padding;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: Align(
                  alignment: Alignment.topCenter,
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(
                      maxWidth: AppDimens.maxContentWidth,
                    ),
                    child: Padding(
                      padding:
                          padding ??
                          const EdgeInsets.symmetric(
                            horizontal: AppDimens.pagePaddingH,
                          ),
                      child: child,
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
