import 'package:flutter/material.dart';
import '../api.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../theme/app_typography.dart';
import '../widgets/app_screen.dart';
import '../widgets/form_message.dart';
import '../widgets/infirmo_button.dart';
import '../widgets/infirmo_dropdown_field.dart';
import '../widgets/infirmo_text_field.dart';

/// Écran de modification des informations du compte.
///
/// Reprend l'habillage de la maquette « Créer un compte » (chevron retour,
/// grand titre, champs libellés, bouton en pied) avec les champs du contrat
/// `/profile` existant : nom professionnel, statut et ville.
class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({
    super.key,
    required this.initialProfile,
    required this.onSave,
    required this.onBack,
  });

  final Profile initialProfile;

  /// Enregistre le profil. Retourne `null` si réussi, sinon le message d'erreur.
  final Future<String?> Function(Profile profile) onSave;

  /// Quitte l'écran (déconnexion + retour à la connexion).
  final Future<void> Function() onBack;

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  static const _roles = [
    InfirmoDropdownOption(value: 'titulaire', label: 'Titulaire'),
    InfirmoDropdownOption(value: 'remplacant', label: 'Remplaçant'),
  ];

  final _form = GlobalKey<FormState>();
  late final TextEditingController _name;
  late final TextEditingController _city;
  late String _role;

  bool _busy = false;
  String? _error;
  String? _notice;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.initialProfile.displayName);
    _city = TextEditingController(text: widget.initialProfile.city);
    _role = widget.initialProfile.role;
  }

  @override
  void dispose() {
    _name.dispose();
    _city.dispose();
    super.dispose();
  }

  String? _required(String? value) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return 'Ce champ est obligatoire.';
    if (text.length > 80 || RegExp(r'[\x00-\x1F\x7F]').hasMatch(text)) {
      return 'Saisissez au maximum 80 caractères, sans caractère de contrôle.';
    }
    return null;
  }

  Future<void> _save() async {
    if (_busy) return;
    setState(() {
      _error = null;
      _notice = null;
    });
    if (!_form.currentState!.validate()) return;

    setState(() => _busy = true);
    final error = await widget.onSave(
      Profile(displayName: _name.text, role: _role, city: _city.text),
    );
    if (!mounted) return;
    setState(() {
      _busy = false;
      _error = error;
      _notice = error == null ? 'Profil enregistré.' : null;
    });
  }

  Future<void> _back() async {
    if (_busy) return;
    setState(() => _busy = true);
    await widget.onBack();
  }

  @override
  Widget build(BuildContext context) {
    return AppScreen(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: AppDimens.gap8),
          Row(
            children: [
              // Chevron 24×24 aligné à 20px du bord (marge de page = 24px).
              Transform.translate(
                offset: const Offset(-4, 0),
                child: _BackButton(onPressed: _busy ? null : _back),
              ),
              const SizedBox(width: AppDimens.gap8),
              const Expanded(
                child: Text(
                  'Modifier mes informations',
                  style: AppText.pageTitle,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimens.gap32),
          Form(
            key: _form,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                InfirmoTextField(
                  key: const Key('display_name'),
                  label: 'Nom professionnel',
                  controller: _name,
                  enabled: !_busy,
                  textInputAction: TextInputAction.next,
                  validator: _required,
                ),
                const SizedBox(height: AppDimens.gap24),
                InfirmoDropdownField<String>(
                  key: const Key('role'),
                  label: 'Statut professionnel',
                  value: _role,
                  options: _roles,
                  enabled: !_busy,
                  onChanged: (value) => setState(() => _role = value ?? _role),
                ),
                const SizedBox(height: AppDimens.gap24),
                InfirmoTextField(
                  key: const Key('city'),
                  label: 'Ville',
                  controller: _city,
                  enabled: !_busy,
                  textInputAction: TextInputAction.done,
                  validator: _required,
                  onFieldSubmitted: (_) => _save(),
                ),
                if (_error != null) ...[
                  const SizedBox(height: AppDimens.gap16),
                  FormMessage(text: _error!),
                ],
                if (_notice != null) ...[
                  const SizedBox(height: AppDimens.gap16),
                  FormMessage(text: _notice!, isError: false),
                ],
                const SizedBox(height: AppDimens.gap32),
                InfirmoButton(
                  key: const Key('save_profile'),
                  label: 'ENREGISTRER',
                  busy: _busy,
                  onPressed: _busy ? null : _save,
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

/// Chevron de retour épais, aligné sur la maquette.
class _BackButton extends StatelessWidget {
  const _BackButton({required this.onPressed});

  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return IconButton(
      key: const Key('signout'),
      onPressed: onPressed,
      tooltip: 'Retour',
      padding: EdgeInsets.zero,
      iconSize: 24,
      visualDensity: VisualDensity.compact,
      constraints: const BoxConstraints.tightFor(width: 24, height: 24),
      icon: const Icon(Icons.chevron_left, size: 24, color: AppColors.ink),
    );
  }
}
