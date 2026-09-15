import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:infirmo/api.dart';
import 'package:infirmo/main.dart';

void main() {
  testWidgets(
    'save, close and sign in again retrieves the backend profile on a narrow screen',
    (tester) async {
      tester.view.physicalSize = const Size(360, 800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      var saved = {
        'display_name': 'Camille Démo',
        'role': 'titulaire',
        'city': 'Nancy',
      };
      var logins = 0;
      InfirmoApi api() => InfirmoApi(
        client: MockClient((request) async {
          if (request.url.path == '/api/auth/login') {
            expect(request.headers['Authorization'], isNull);
            expect(jsonDecode(request.body)['password'], 'Infirmo-demo-2026!');
            logins++;
            return http.Response(
              jsonEncode({
                'access_token': 'synthetic-$logins',
                'token_type': 'bearer',
              }),
              200,
            );
          }
          expect(request.headers['Authorization'], 'Bearer synthetic-$logins');
          if (request.method == 'PUT') {
            saved = Map<String, String>.from(jsonDecode(request.body));
          }
          return http.Response(
            jsonEncode(saved),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }),
      );
      Future<void> login() async {
        await tester.enterText(
          find.byKey(const Key('password')),
          'Infirmo-demo-2026!',
        );
        await tester.ensureVisible(find.text('Se connecter'));
        await tester.tap(find.text('Se connecter'));
        await tester.pumpAndSettle();
      }

      await tester.pumpWidget(InfirmoApp(api: api()));
      await login();
      expect(find.text('Camille Démo'), findsOneWidget);
      await tester.enterText(
        find.byKey(const Key('display_name')),
        'Alex Exemple',
      );
      await tester.enterText(find.byKey(const Key('city')), 'Metz');
      await tester.ensureVisible(find.text('Enregistrer le profil'));
      await tester.tap(find.text('Enregistrer le profil'));
      await tester.pumpAndSettle();
      expect(saved['display_name'], 'Alex Exemple');
      expect(saved['city'], 'Metz');
      expect(find.textContaining('Profil enregistré.'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      await tester.pumpWidget(InfirmoApp(api: api()));
      expect(find.text('Bienvenue sur INFIRMO'), findsOneWidget);
      await login();
      expect(find.text('Alex Exemple'), findsOneWidget);
      expect(find.text('Metz'), findsOneWidget);
      expect(logins, 2);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('validates login and shows safe API error', (tester) async {
    var requests = 0;
    final api = InfirmoApi(
      client: MockClient((request) async {
        requests++;
        return http.Response(
          '{"detail":"internal-data-must-not-be-shown"}',
          401,
        );
      }),
    );
    await tester.pumpWidget(InfirmoApp(api: api));
    await tester.ensureVisible(find.text('Se connecter'));
    await tester.tap(find.text('Se connecter'));
    await tester.pumpAndSettle();
    expect(requests, 0);
    expect(
      find.text('Saisissez un mot de passe (128 caractères maximum).'),
      findsOneWidget,
    );
    await tester.enterText(find.byKey(const Key('password')), 'incorrect');
    await tester.ensureVisible(find.text('Se connecter'));
    await tester.tap(find.text('Se connecter'));
    await tester.pumpAndSettle();
    expect(requests, 1);
    expect(
      find.text('Adresse e-mail ou mot de passe incorrect.'),
      findsOneWidget,
    );
    expect(find.textContaining('internal-data'), findsNothing);
  });

  test('logout revokes bearer session and new client has no token', () async {
    final calls = <http.Request>[];
    final api = InfirmoApi(
      client: MockClient((request) async {
        calls.add(request);
        if (request.url.path.endsWith('/login')) {
          return http.Response('{"access_token":"synthetic"}', 200);
        }
        return http.Response('', 204);
      }),
    );
    await api.login('demo@infirmo.example', 'Infirmo-demo-2026!');
    await api.logout();
    expect(calls.last.url.path, '/api/auth/logout');
    expect(calls.last.headers['Authorization'], 'Bearer synthetic');
    await api.login('demo@infirmo.example', 'Infirmo-demo-2026!');
    expect(calls.last.headers['Authorization'], isNull);
    api.close();
  });
}
