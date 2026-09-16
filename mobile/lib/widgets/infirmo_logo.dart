import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_typography.dart';

/// Logo « INFIRMO ».
class InfirmoLogo extends StatelessWidget {
  const InfirmoLogo({super.key, this.style});

  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    final textStyle = AppText.logo.merge(style);
    final fontSize = textStyle.fontSize ?? AppText.logo.fontSize!;

    return Semantics(
      label: 'INFIRMO',
      image: true,
      child: ExcludeSemantics(
        child: Stack(
          alignment: Alignment.center,
          children: [
            Positioned(
              left: 0,
              right: 0,
              bottom: fontSize * 0.10,
              height: fontSize * 0.42,
              child: Container(color: AppColors.highlight),
            ),
            Text('INFIRMO', style: textStyle, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}
