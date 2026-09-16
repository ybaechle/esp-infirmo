# Preuves de vérification

Date : 2026-09-15. Environnement : poste de développement Windows, Docker Desktop Linux. Ces vérifications locales ne constituent pas une installation indépendante sur une machine propre.

## Baseline avant changement

- Backend : 4 tests réussis; IA : 1 test réussi; lint et format des deux modules réussis.
- `docker compose --env-file .env.example config --quiet` : code 0.
- Docker Engine initialement absent; Docker Desktop démarré, serveur 29.5.3 disponible.
- Quatre runs GitHub `develop` bloqués avant exécution : `The job was not started because an Actions budget is preventing further use.` Les données datées sont dans `github.json`.
- Compte GitHub : lecture/écriture du dépôt, pas de permission administrateur. Branches main/develop non protégées lors du constat.

## Résultats locaux de la livraison

| Vérification | Résultat observé | Portée |
| --- | --- | --- |
| Backend Python 3.12.13 + PostgreSQL 17 + Redis 7 | 27 tests réussis en 101,52 s; couverture application 95,24 % | Migrations aller/retour, seed idempotent, auth/isolation, validation, révocation, persistance |
| Backend Ruff lint / format | Réussite | Sources, migrations et tests |
| CLI migration puis seed | Codes 0 | Base PostgreSQL réelle; compte fictif prêt, profil existant préservé |
| IA Python 3.12 | 1 test réussi; couverture 100 % de cinq instructions | Santé du service uniquement, aucune transcription |
| Flutter analyse / tests | Analyse sans problème; 3 tests réussis | Client HTTP et widgets avec fixture persistante simulée |
| Flutter web release | Build réussi en 153,1 s | Sources Flutter, polices locales et ressources sans CDN |
| Build APK Android sur l'hôte | Échec initial : SDK Android absent | Constat conservé; la reprise Docker ci-dessous utilise son propre SDK |
| Build APK Android dans Docker | Code 0; 148 406 941 octets; SHA-256 du fichier copié vérifié | Flutter 3.44 / Android 36, `88a5abb`; [preuve et chemin APK](android-build.json); aucun essai appareil |
| Reporting | 3 tests réussis | Inconnues, calcul ETC/écart, classification CI |
| Compose local | Clone distant `6789507`, volume vide, build et démarrage code 0; cinq services sains | Poste existant et images de base en cache; PostgreSQL 16.4/PostGIS du Compose |
| Compose staging | Configuration valide | Aucun déploiement distant |
| Contrôle API public | Code 0; connexion, écriture, nouvelle session et révocation réussies | Proxy web et PostgreSQL réels |
| Widgets Flutter avec API réelle | Analyse sans problème; `00:05 +1: All tests passed!` | Exécution séquentielle; nouvelle instance de l'application, profil relu et restauration vérifiée |
| Arrêt/recréation des conteneurs | Profil modifié conservé après `docker compose down` puis `up --wait`; restauration réussie | Volume PostgreSQL conservé, seed rejoué sans écraser le profil |
| Distribution web | HTTP 200 pour HTML, bootstrap, application JS, CanvasKit WASM et police Roboto | Fichiers non vides; aucune assimilation à une validation visuelle |
| Navigateur Chrome 152 | Connexion, erreur 401 attendue, modification nom/ville/rôle, déconnexion/reconnexion et rechargement réussis | Playwright réel, 390 × 844 puis 360 × 800; [preuve](browser.json) et captures |
| Régression navigateur `88a5abb` | Message de validation complet sur deux lignes à 360 × 800; zéro erreur console | [Capture vérifiée](browser-validation-fixed.png); analyse Flutter et trois tests également réussis |
| Sauvegarde/restauration PostgreSQL | Dump 9 725 octets; modification fictive annulée par restauration; API ensuite réussie | Scripts réels sur le projet jetable; aucun serveur distant |
| Protections GitHub | Contrôle code 1 : exigences absentes sur main et develop | Règles applicables et protection classique; [preuve datée](branch-protection.json), aucune écriture de test |
| Application du ruleset | GitHub rejette la demande avec `HTTP 404: Not Found` | Rôle `student`; [réponse API](branch-protection-apply.json); aucune règle créée |
| Reproduction avec caches vides | Trois builds terminés, 0 % de cache; cinq services sains; API, navigateur et reprise réussis | [Relevé complet](cold-start.md), `bf55fcd`; deux corrections de l'outillage, code du premier Compose inconnu |
| Workflows et scripts | YAML parsé; 32 étapes shell vérifiées; test opérationnel réussi | Stubs Docker pour backup/deploy; aucun déploiement distant déduit |

Commande backend : `uv run python -m pytest -q --junitxml=test-results.xml`, avec `TEST_DATABASE_URL` et `REDIS_URL` sur des conteneurs jetables dédiés. Rapports de travail : `backend/coverage.xml`, `backend/test-results.xml`; les rapports XML de CI sont publiés comme artefacts.

L'exécution backend a produit cinq avertissements : un avertissement Starlette/httpx conservé et quatre avertissements Alembic corrigés par `path_separator=os`; la CLI migration a ensuite réussi. Avertissement restant : `Using httpx with starlette.testclient is deprecated; install httpx2 instead.`

Le test Android a retourné : `[!] No Android SDK found. Try setting the ANDROID_HOME environment variable.`

La reprise en conteneur a ensuite réussi : `Built build/app/outputs/flutter-apk/app-debug.apk`. Durée totale 992,66 s, incluant les téléchargements Gradle/NDK/CMake; assemblage Gradle 944 s. Le SDK de l'hôte n'a pas été modifié. L'APK debug vise le proxy local via `10.0.2.2:8080/api`, adresse de l'émulateur; aucune installation ni exécution native n'est attestée.

## Reprises et limites de mesure

Révision applicative testée : `67895074d4c8541ea59bde8bd6d283e874fd4ea4`. Le test explicite ajouté dans `mobile/test_live/profile_live_test.dart` exerce cette application avec son vrai backend; son analyse ciblée et son exécution séquentielle ont réussi. Commande : `flutter test test_live/profile_live_test.dart --dart-define=LIVE_API_BASE_URL=http://localhost:8080/api` depuis `mobile/`.

1. `developer-compose-1`, révision `9924664` : échec de `up --wait`, mobile `unhealthy`. `wget localhost` refusait la connexion, `127.0.0.1` réussissait. Sondes corrigées au commit `67baa8e` (DL-011).
2. `developer-clone-1`, révision `67baa8e` : échec de `up --wait` sur base vide. La sonde PostgreSQL validait le serveur temporaire Unix avant l'ouverture TCP; la migration backend recevait `connection refused`. Sonde TCP corrigée au commit `6789507` (DL-012).
3. `developer-clone-2`, clone distant de `6789507` et nouveau volume vide : commande exacte `docker compose up -d --build --wait --wait-timeout 300`, code 0, cinq services sains. La fenêtre horodatée clone/configuration/build/démarrage dure **72,85 secondes**. Les images de base étaient en cache; cette durée exclut les essais API/widgets et le redémarrage. Ce n'est pas la durée d'onboarding indépendant.
4. Une exécution API concomitante au test de widgets a échoué avec `RuntimeError: Profile update did not persist across sessions`. Les deux contrôles modifiaient le même compte. La procédure impose désormais leur exécution successive; API puis widgets réels ont tous deux réussi séparément (DL-013).
5. Un profil fictif distinct a été sauvegardé avant `docker compose down`. Après recréation par `docker compose up -d --wait --wait-timeout 300`, une nouvelle connexion l'a retrouvé; le profil précédent a été restauré et les sessions de contrôle révoquées.

La [preuve structurée](developer-rehearsal.json) contient révision, bornes horaires et résultats. `runs.csv` conserve les tentatives. Le comptage exhaustif des ajustements n'avait pas été établi avant ces essais de développement : leur PDR reste **non mesuré**, sans zéro reconstruit après coup. Le protocole du pair impose ce comptage dès le départ.

La reprise technique ultérieure sur un démon Docker neuf est mesurée séparément : **2 ajustements / 7 actions = 28,57 %**, préparation du banc exclue. La fenêtre d'observation complète est de 31,14 minutes, avec pauses et contention de l'hôte; le build mobile a pris 18 min 26 s. Ce résultat ne prouve pas la cible CI de 15 minutes. Le collecteur Windows a perdu le code de sortie initial, mais les historiques BuildKit ont confirmé les builds complets sans cache; les contrôles API/navigateur et arrêt/reprise ont ensuite réussi. Voir [la preuve isolée](cold-start.md).

Lors de la première livraison, le contrôle navigateur n'avait pas été exécuté : la surface intégrée était indisponible. Le connecteur Playwright a ensuite été découvert et utilisé pour le parcours réel décrit ci-dessus. Le test Flutter initial reste une preuve distincte. Le navigateur a révélé un message de validation tronqué (DL-015), corrigé avec un test de régression à 360 px. Ces essais restent distincts de l'acceptation par un pair humain.

## Limites externes

- Test par un pair sur machine propre : non réalisé.
- Déploiement sur le serveur staging et validation distante : non réalisés.
- Rétablissement du budget Actions et protection des branches : nécessitent l'administrateur.
- Heures réelles, ETC et rétrospective : attendent les observations de l'équipe. Le [budget planifié du PDF](workload-baseline.md) est disponible : 147 h par personne, 1 029 h équipe, plus 220,5 h de réserve.

Les API GitHub ont également retourné zéro secret de dépôt et zéro environnement configuré le 15/09/2026. Aucun serveur staging exploitable n'est identifié dans les éléments contrôlés. L'absence de capacité Actions et de droits administrateur ne bloque pas les contrôles locaux décrits ici; elle reste une dépendance externe de la DoD hébergée.

La PR de livraison est [la PR #1](https://github.com/EpitechMscProPromo2027/T-ESP-901-NCY-9-1-T-ESP-901-1/pull/1), en brouillon. Au commit `6789507`, les runs `34975899210` et `34975899622` sont de nouveau bloqués avant toute étape par le budget Actions, avec le même message cité ci-dessus. Aucun succès local ne remplace cette porte de qualité hébergée.

Contrôle final : le run GitHub `34981633829` au commit `74afee3` confirme le même blocage de budget avant démarrage. Le conteneur Docker isolé et son seul volume de cache ont été supprimés après vérification; les preuves et l’APK sont conservés. Aucun nettoyage global des caches ni déploiement distant n’a été exécuté.
