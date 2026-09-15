import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'api.dart';

void main() => runApp(InfirmoApp(api: InfirmoApi()));

class InfirmoApp extends StatelessWidget {
  const InfirmoApp({super.key, required this.api});
  final InfirmoApi api;
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'INFIRMO — Démonstration',
    debugShowCheckedModeBanner: false,
    locale: const Locale('fr'),
    supportedLocales: const [Locale('fr')],
    localizationsDelegates: GlobalMaterialLocalizations.delegates,
    theme: ThemeData(
      fontFamily: 'Roboto',
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff006b60)),
      scaffoldBackgroundColor: const Color(0xfff5f8f7),
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(double.infinity, 52),
        ),
      ),
    ),
    home: ProfileDemo(api: api),
  );
}

class ProfileDemo extends StatefulWidget {
  const ProfileDemo({super.key, required this.api});
  final InfirmoApi api;
  @override
  State<ProfileDemo> createState() => _ProfileDemoState();
}

class _ProfileDemoState extends State<ProfileDemo> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController(text: 'demo@infirmo.example');
  final _password = TextEditingController();
  final _name = TextEditingController();
  final _city = TextEditingController();
  String _role = 'titulaire';
  bool _signedIn = false;
  bool _loaded = false;
  bool _busy = false;
  bool _obscure = true;
  String? _error;
  String? _notice;

  @override
  void dispose() {
    for (final controller in [_email, _password, _name, _city]) {
      controller.dispose();
    }
    widget.api.close();
    super.dispose();
  }

  void _setProfile(Profile profile) {
    _name.text = profile.displayName;
    _city.text = profile.city;
    _role = profile.role;
    _loaded = true;
  }

  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      await action();
    } on ApiException catch (error) {
      if (!mounted) return;
      if (error.unauthorized) {
        _signedIn = false;
        _loaded = false;
        _name.clear();
        _city.clear();
      }
      _error = error.message;
    } catch (_) {
      if (!mounted) return;
      _error = 'Réponse du serveur invalide. Réessayez.';
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _login() {
    if (!_form.currentState!.validate()) return;
    _run(() async {
      await widget.api.login(_email.text, _password.text);
      if (!mounted) return;
      _password.clear();
      _signedIn = true;
      final profile = await widget.api.profile();
      if (mounted) _setProfile(profile);
    });
  }

  void _save() {
    if (!_form.currentState!.validate()) return;
    _run(() async {
      final saved = await widget.api.save(
        Profile(displayName: _name.text, role: _role, city: _city.text),
      );
      if (!mounted) return;
      _setProfile(saved);
      _notice =
          'Profil enregistré. Vous le retrouverez à votre prochaine connexion.';
    });
  }

  String? _required(String? value) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return 'Ce champ est obligatoire.';
    if (text.length > 80 || RegExp(r'[\x00-\x1F\x7F]').hasMatch(text)) {
      return 'Saisissez au maximum 80 caractères, sans caractère de contrôle.';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 24),
                Text(
                  'INFIRMO',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: const Color(0xff006b60),
                  ),
                ),
                const SizedBox(height: 8),
                const Text('Le réseau professionnel des infirmiers libéraux'),
                const SizedBox(height: 24),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xffe0eeea),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Text(
                    'Données fictives · Démonstration v0.1\nUtilisez uniquement des informations inventées. Aucun dossier patient.',
                  ),
                ),
                const SizedBox(height: 28),
                Text(
                  _signedIn
                      ? 'Mon profil professionnel'
                      : 'Bienvenue sur INFIRMO',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 8),
                Text(
                  _signedIn
                      ? 'Modifiez votre profil de démonstration.'
                      : 'Connectez-vous pour préparer votre profil professionnel.',
                ),
                const SizedBox(height: 24),
                if (_busy)
                  const LinearProgressIndicator(
                    semanticsLabel: 'Opération en cours',
                  ),
                if (_error != null) _message(_error!, error: true),
                if (_notice != null) _message(_notice!),
                Form(
                  key: _form,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: _signedIn ? _profileFields() : _loginFields(),
                  ),
                ),
                const SizedBox(height: 24),
                const Text(
                  'Votre session reste en mémoire uniquement. Après fermeture ou actualisation, reconnectez-vous pour retrouver le profil enregistré.',
                  style: TextStyle(fontSize: 13),
                ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    ),
  );
  Widget _message(String text, {bool error = false}) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 16),
    child: Semantics(
      liveRegion: true,
      child: Text(
        text,
        style: TextStyle(
          color: error
              ? Theme.of(context).colorScheme.error
              : const Color(0xff005449),
        ),
      ),
    ),
  );
  List<Widget> _loginFields() => [
    TextFormField(
      key: const Key('email'),
      controller: _email,
      enabled: !_busy,
      decoration: const InputDecoration(labelText: 'Adresse e-mail'),
      keyboardType: TextInputType.emailAddress,
      textInputAction: TextInputAction.next,
      autocorrect: false,
      validator: (value) =>
          value == null ||
              value.trim().length > 254 ||
              !RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(value.trim())
          ? 'Saisissez une adresse e-mail valide.'
          : null,
    ),
    const SizedBox(height: 16),
    TextFormField(
      key: const Key('password'),
      controller: _password,
      enabled: !_busy,
      obscureText: _obscure,
      enableSuggestions: false,
      autocorrect: false,
      decoration: InputDecoration(
        labelText: 'Mot de passe',
        suffixIcon: IconButton(
          tooltip: _obscure
              ? 'Afficher le mot de passe'
              : 'Masquer le mot de passe',
          onPressed: () => setState(() => _obscure = !_obscure),
          icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
        ),
      ),
      textInputAction: TextInputAction.done,
      onFieldSubmitted: (_) => _login(),
      validator: (value) => value == null || value.isEmpty || value.length > 128
          ? 'Saisissez un mot de passe (128 caractères maximum).'
          : null,
    ),
    const SizedBox(height: 16),
    const SelectableText(
      'Compte fictif : demo@infirmo.example\nMot de passe : Infirmo-demo-2026!',
    ),
    const SizedBox(height: 24),
    FilledButton(
      onPressed: _busy ? null : _login,
      child: const Text('Se connecter'),
    ),
  ];
  List<Widget> _profileFields() => [
    if (_loaded) ...[
      TextFormField(
        key: const Key('display_name'),
        controller: _name,
        enabled: !_busy,
        decoration: const InputDecoration(
          labelText: 'Nom professionnel fictif',
        ),
        textInputAction: TextInputAction.next,
        validator: _required,
      ),
      const SizedBox(height: 16),
      DropdownButtonFormField<String>(
        key: ValueKey('role-$_role'),
        initialValue: _role,
        decoration: const InputDecoration(labelText: 'Statut professionnel'),
        items: const [
          DropdownMenuItem(value: 'titulaire', child: Text('Titulaire')),
          DropdownMenuItem(value: 'remplacant', child: Text('Remplaçant')),
        ],
        onChanged: _busy ? null : (value) => setState(() => _role = value!),
      ),
      const SizedBox(height: 16),
      TextFormField(
        key: const Key('city'),
        controller: _city,
        enabled: !_busy,
        decoration: const InputDecoration(labelText: 'Ville'),
        textInputAction: TextInputAction.done,
        validator: _required,
        onFieldSubmitted: (_) => _save(),
      ),
      const SizedBox(height: 24),
      FilledButton(
        onPressed: _busy ? null : _save,
        child: const Text('Enregistrer le profil'),
      ),
    ] else
      OutlinedButton(
        onPressed: _busy
            ? null
            : () => _run(() async {
                final profile = await widget.api.profile();
                if (mounted) _setProfile(profile);
              }),
        child: const Text('Recharger le profil'),
      ),
    const SizedBox(height: 12),
    TextButton(
      onPressed: _busy
          ? null
          : () => _run(() async {
              await widget.api.logout();
              if (!mounted) return;
              _signedIn = false;
              _loaded = false;
              _name.clear();
              _city.clear();
              _notice = 'Vous êtes déconnecté.';
            }),
      child: const Text('Se déconnecter'),
    ),
  ];
}
