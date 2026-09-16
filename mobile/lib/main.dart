import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'api.dart';
import 'screens/edit_profile_screen.dart';
import 'screens/login_screen.dart';
import 'theme/app_theme.dart';

void main() => runApp(InfirmoApp(api: InfirmoApi()));

class InfirmoApp extends StatelessWidget {
  const InfirmoApp({super.key, required this.api});

  final InfirmoApi api;

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'INFIRMO',
    debugShowCheckedModeBanner: false,
    locale: const Locale('fr'),
    supportedLocales: const [Locale('fr')],
    localizationsDelegates: GlobalMaterialLocalizations.delegates,
    theme: AppTheme.light,
    home: AppRoot(api: api),
  );
}

/// Aiguille entre connexion et profil selon la session.
class AppRoot extends StatefulWidget {
  const AppRoot({super.key, required this.api});

  final InfirmoApi api;

  @override
  State<AppRoot> createState() => _AppRootState();
}

class _AppRootState extends State<AppRoot> {
  Profile? _profile;

  @override
  void dispose() {
    widget.api.close();
    super.dispose();
  }

  Future<String?> _signIn(String email, String password) async {
    try {
      await widget.api.login(email, password);
      final profile = await widget.api.profile();
      if (mounted) setState(() => _profile = profile);
      return null;
    } on ApiException catch (error) {
      return error.message;
    } catch (_) {
      return 'Réponse du serveur invalide. Réessayez.';
    }
  }

  Future<String?> _saveProfile(Profile profile) async {
    try {
      final saved = await widget.api.save(profile);
      if (mounted) setState(() => _profile = saved);
      return null;
    } on ApiException catch (error) {
      if (error.unauthorized && mounted) setState(() => _profile = null);
      return error.message;
    } catch (_) {
      return 'Réponse du serveur invalide. Réessayez.';
    }
  }

  Future<void> _signOut() async {
    try {
      await widget.api.logout();
    } catch (_) {
      // Session déjà perdue : on revient à la connexion.
    }
    if (mounted) setState(() => _profile = null);
  }

  @override
  Widget build(BuildContext context) {
    final profile = _profile;
    if (profile == null) {
      return LoginScreen(onSubmit: _signIn);
    }
    return EditProfileScreen(
      initialProfile: profile,
      onSave: _saveProfile,
      onBack: _signOut,
    );
  }
}
