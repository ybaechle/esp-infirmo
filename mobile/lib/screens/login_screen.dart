import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../theme/app_typography.dart';
import '../widgets/app_screen.dart';
import '../widgets/form_message.dart';
import '../widgets/infirmo_button.dart';
import '../widgets/infirmo_logo.dart';
import '../widgets/infirmo_text_field.dart';

/// Écran de connexion INFIRMO (maquette « Login »).
///
/// Le parent fournit [onSubmit] qui tente l'authentification et renvoie un
/// message d'erreur à afficher (ou `null` en cas de succès).
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.onSubmit});

  /// Tente la connexion. Retourne `null` si réussie, sinon le message d'erreur.
  final Future<String?> Function(String email, String password) onSubmit;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();

  bool _busy = false;
  bool _obscure = true;

  /// Erreur d'authentification renvoyée par le backend (bordures rouges des
  /// deux champs + message global sous le formulaire).
  String? _authError;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_busy) return;
    setState(() => _authError = null);
    if (!_form.currentState!.validate()) return;

    setState(() => _busy = true);
    final error = await widget.onSubmit(_email.text, _password.text);
    if (!mounted) return;
    setState(() {
      _busy = false;
      _authError = error;
    });
    if (error == null) _password.clear();
  }

  String? _validateEmail(String? value) {
    final text = value?.trim() ?? '';
    if (text.length > 254 ||
        !RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(text)) {
      return 'Saisissez une adresse e-mail valide.';
    }
    return null;
  }

  String? _validatePassword(String? value) {
    if (value == null || value.isEmpty || value.length > 128) {
      return 'Saisissez un mot de passe (128 caractères maximum).';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return AppScreen(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 64),
          const Center(child: InfirmoLogo()),
          const SizedBox(height: AppDimens.gap16),
          const Text(
            'LE RÉSEAU DES INFIRMIERS, LES REMPLACEMENTS SIMPLIFIÉS.',
            style: AppText.tagline,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppDimens.gap40),
          Form(
            key: _form,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                InfirmoTextField(
                  key: const Key('email'),
                  label: 'E-mail',
                  controller: _email,
                  enabled: !_busy,
                  hasError: _authError != null,
                  keyboardType: TextInputType.emailAddress,
                  textInputAction: TextInputAction.next,
                  autocorrect: false,
                  enableSuggestions: false,
                  autofillHints: const [AutofillHints.username],
                  validator: _validateEmail,
                ),
                const SizedBox(height: AppDimens.gap24),
                InfirmoTextField(
                  key: const Key('password'),
                  label: 'Mot de passe',
                  controller: _password,
                  enabled: !_busy,
                  hasError: _authError != null,
                  obscureText: _obscure,
                  autocorrect: false,
                  enableSuggestions: false,
                  autofillHints: const [AutofillHints.password],
                  textInputAction: TextInputAction.done,
                  onFieldSubmitted: (_) => _submit(),
                  validator: _validatePassword,
                  suffixIcon: IconButton(
                    tooltip: _obscure
                        ? 'Afficher le mot de passe'
                        : 'Masquer le mot de passe',
                    onPressed: () => setState(() => _obscure = !_obscure),
                    icon: Icon(
                      _obscure
                          ? Icons.visibility_outlined
                          : Icons.visibility_off_outlined,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
                if (_authError != null) ...[
                  const SizedBox(height: AppDimens.gap12),
                  FormMessage(text: _authError!),
                ],
                const SizedBox(height: AppDimens.gap24),
                // TEMP : identifiants de démonstration affichés à la demande,
                // à retirer ultérieurement.
                const SelectableText(
                  'Compte fictif : demo@infirmo.example\n'
                  'Mot de passe : Infirmo-demo-2026!',
                  style: AppText.hint,
                ),
                const SizedBox(height: AppDimens.gap24),
                InfirmoButton(
                  key: const Key('login_submit'),
                  label: 'SE CONNECTER',
                  busy: _busy,
                  onPressed: _busy ? null : _submit,
                ),
              ],
            ),
          ),
          const SizedBox(height: AppDimens.gap40),
        ],
      ),
    );
  }
}
