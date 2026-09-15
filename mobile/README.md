# INFIRMO mobile — v0.1

Application Flutter de démonstration **avec données fictives uniquement**. Android
est la cible mobile ; la compilation web distribue la même application pour les
tests externes. Aucune donnée réelle de professionnel ou de patient ne doit être
saisie dans cet environnement local, qui ne constitue pas un hébergement HDS.

## Parcours livré

1. Se connecter : `demo@infirmo.example` / `Infirmo-demo-2026!`.
2. Modifier le nom fictif, le statut (titulaire/remplaçant) et la ville.
3. Enregistrer le profil : les données sont sauvegardées par l'API.
4. Fermer/actualiser puis se reconnecter : le profil sauvegardé est rechargé.
5. Se déconnecter : la session est révoquée côté serveur.

Le jeton reste uniquement en mémoire. Aucun stockage local du jeton, du mot de
passe ou du profil ; aucune télémétrie. Si la déconnexion échoue, un message invite
à réessayer. Les sessions perdues à la fermeture expirent côté serveur.

## Démarrage local recommandé

Depuis la racine du dépôt, suivre les instructions Docker Compose dans
[`infra/README.md`](../infra/README.md). Ouvrir `http://localhost:8080`.
Le serveur web relaie `/api/` vers le backend, sans CORS ni dépendance externe
à l'exécution. Le moteur web Flutter est livré dans l'image.
Les polices Roboto sont embarquées avec leur licence. Les caractères hors de
leur couverture nécessitent une police locale supplémentaire ; aucun repli vers
un service de polices tiers n'est configuré.

## Développement Flutter

Version de référence : **Flutter 3.44.0 / Dart 3.12.0**. Les dépendances sont
verrouillées par `pubspec.lock`.

```sh
cd mobile
flutter pub get --enforce-lockfile
flutter analyze
flutter test
flutter build web --release --no-web-resources-cdn
```

Pour Android, installer le SDK Android et un émulateur, puis utiliser l'URL du
proxy local accessible depuis l'émulateur :

```sh
flutter run -d <android-device-id> --dart-define=API_BASE_URL=http://10.0.2.2:8080/api
```

Le HTTP est autorisé uniquement dans le manifeste Android **debug**, pour cette
démonstration synthétique locale. Une compilation de distribution demande une
URL HTTPS via `API_BASE_URL`. La configuration de signature Android générée reste
une signature de développement ; aucune publication sur un store n'est prévue.
Les commandes Android nécessitent un SDK installé et ne sont pas validées sur une
machine sans celui-ci. Sur appareil physique, utiliser une URL de proxy accessible
à cet appareil ; le Compose par défaut reste limité à localhost.

## Périmètre

Authentification d'un compte de démonstration et profil professionnel uniquement.
Les remplacements, candidatures, messages, transmissions et l'IA ne sont pas
implémentés dans cette version. Les maquettes Figma restent la référence produit ;
cette première interface fonctionnelle ne revendique pas leur reproduction.

Les tests utilisent un serveur HTTP simulé pour vérifier le contrat, l'édition,
la reconnexion après fermeture, la validation, les erreurs et la déconnexion.
La persistance réelle se vérifie avec le parcours Docker et les tests backend.
