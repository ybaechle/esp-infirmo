import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:infirmo/api.dart';
import 'package:infirmo/main.dart';

// The regular widget-test binding replaces HTTP with 400 responses.
class _LiveHttpBinding extends AutomatedTestWidgetsFlutterBinding {
  @override
  bool get overrideHttpClient => false;
}

void main() {
  _LiveHttpBinding();

  testWidgets('live profile survives sign-out and a new application instance', (
    tester,
  ) async {
    const baseUrl = String.fromEnvironment('LIVE_API_BASE_URL');
    final uri = Uri.tryParse(baseUrl);
    expect(
      uri != null &&
          uri.hasAuthority &&
          {'http', 'https'}.contains(uri.scheme) &&
          uri.path.endsWith('/api'),
      isTrue,
      reason:
          'Required: --dart-define=LIVE_API_BASE_URL=http://localhost:8080/api',
    );
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    // Real socket completion and the client's timeout need real asynchronous time.
    await tester.runAsync(() async {
      Future<void> waitFor(Finder finder) async {
        final deadline = DateTime.now().add(const Duration(seconds: 20));
        do {
          await tester.pump();
          if (finder.evaluate().isNotEmpty) return;
          await Future<void>.delayed(const Duration(milliseconds: 100));
        } while (DateTime.now().isBefore(deadline));
        expect(finder, findsOneWidget, reason: 'Live API flow did not finish.');
      }

      Future<void> press(String label) async {
        final button = find.text(label);
        await tester.ensureVisible(button);
        await tester.tap(button);
      }

      Future<void> login() async {
        await tester.enterText(
          find.byKey(const Key('email')),
          'demo@infirmo.example',
        );
        await tester.enterText(
          find.byKey(const Key('password')),
          'Infirmo-demo-2026!',
        );
        await press('Se connecter');
        await waitFor(find.byKey(const Key('city')));
      }

      final cleanup = InfirmoApi(baseUrl: baseUrl);
      var uiApi = InfirmoApi(baseUrl: baseUrl);
      Profile? original;
      var cleanupSignedIn = false;
      var uiSignedIn = false;
      try {
        await cleanup.login('demo@infirmo.example', 'Infirmo-demo-2026!');
        cleanupSignedIn = true;
        original = await cleanup.profile();
        final name = original.displayName == 'Alex Test Interface'
            ? 'Camille Test Interface'
            : 'Alex Test Interface';
        final city = original.city == 'Metz' ? 'Nancy' : 'Metz';

        await tester.pumpWidget(InfirmoApp(api: uiApi));
        await login();
        uiSignedIn = true;
        await tester.enterText(find.byKey(const Key('display_name')), name);
        await tester.enterText(find.byKey(const Key('city')), city);
        await press('Enregistrer le profil');
        await waitFor(find.textContaining('Profil enregistré.'));
        await press('Se déconnecter');
        await waitFor(find.text('Se connecter'));
        uiSignedIn = false;

        await tester.pumpWidget(const SizedBox());
        uiApi = InfirmoApi(baseUrl: baseUrl);
        await tester.pumpWidget(InfirmoApp(api: uiApi));
        expect(find.text('Bienvenue sur INFIRMO'), findsOneWidget);
        await login();
        uiSignedIn = true;
        expect(
          tester
              .widget<TextFormField>(find.byKey(const Key('display_name')))
              .controller!
              .text,
          name,
        );
        expect(
          tester
              .widget<TextFormField>(find.byKey(const Key('city')))
              .controller!
              .text,
          city,
        );
        expect((await cleanup.profile()).displayName, name);
        expect(tester.takeException(), isNull);
        await press('Se déconnecter');
        await waitFor(find.text('Se connecter'));
        uiSignedIn = false;
      } finally {
        try {
          if (original != null) {
            await cleanup.save(original);
            expect((await cleanup.profile()).toJson(), original.toJson());
          }
          if (uiSignedIn) await uiApi.logout();
          if (cleanupSignedIn) await cleanup.logout();
        } finally {
          await tester.pumpWidget(const SizedBox());
          cleanup.close();
          uiApi.close();
        }
      }
    });
  });
}
