# Preuves de vérification

Date : 2026-09-15. Environnement : poste de développement Windows, Docker Desktop Linux. Ces vérifications locales ne constituent pas une installation indépendante sur une machine propre.

## Baseline avant changement

- Backend : 4 tests réussis; IA : 1 test réussi; lint et format des deux modules réussis.
- `docker compose --env-file .env.example config --quiet` : code 0.
- Docker Engine initialement absent; Docker Desktop démarré, serveur 29.5.3 disponible.
- Quatre runs GitHub `develop` bloqués avant exécution : `The job was not started because an Actions budget is preventing further use.` Les données datées sont dans `github.json`.
- Compte GitHub : lecture/écriture du dépôt, pas de permission administrateur. Branches main/develop non protégées lors du constat.

## Livraison en cours

| Vérification | Résultat observé | Portée |
| --- | --- | --- |
| Backend Python 3.12.13 + PostgreSQL 17 + Redis 7 | 27 tests réussis en 101,52 s; couverture application 95,24 % | Migrations aller/retour, seed idempotent, auth/isolation, validation, révocation, persistance |
| Backend Ruff lint / format | Réussite | Sources, migrations et tests |
| CLI migration puis seed | Codes 0 | Base PostgreSQL réelle; compte fictif prêt, profil existant préservé |
| IA Python 3.12 | 1 test réussi; couverture 100 % de cinq instructions | Santé du service uniquement, aucune transcription |
| Flutter analyse / tests | Analyse sans problème; 3 tests réussis | Client HTTP et widgets avec fixture persistante simulée |
| Flutter web release | Build réussi en 153,1 s | Sources Flutter, polices locales et ressources sans CDN |
| Build APK Android | Échec : SDK Android absent | Non validé; prérequis documenté |
| Reporting | 3 tests réussis | Inconnues, calcul ETC/écart, classification CI |
| Compose local et staging | Configuration valide | Validation statique uniquement à ce stade |
| Workflows et scripts | YAML parsé; 32 étapes shell vérifiées; test opérationnel réussi | Stubs Docker pour backup/deploy; aucun déploiement distant déduit |

Commande backend : `uv run python -m pytest -q --junitxml=test-results.xml`, avec `TEST_DATABASE_URL` et `REDIS_URL` sur des conteneurs jetables dédiés. Rapports de travail : `backend/coverage.xml`, `backend/test-results.xml`; les rapports XML de CI sont publiés comme artefacts.

L'exécution backend a produit cinq avertissements : un avertissement Starlette/httpx conservé et quatre avertissements Alembic corrigés par `path_separator=os`; la CLI migration a ensuite réussi. Avertissement restant : `Using httpx with starlette.testclient is deprecated; install httpx2 instead.`

Le test Android a retourné : `[!] No Android SDK found. Try setting the ANDROID_HOME environment variable.`

Le parcours complet dans les conteneurs et le navigateur est encore en cours de vérification. Ne pas assimiler les tests Flutter simulés à une preuve de persistance réelle.

## Limites externes

- Test par un pair sur machine propre : non réalisé.
- Déploiement sur le serveur staging et validation distante : non réalisés.
- Rétablissement du budget Actions et protection des branches : nécessitent l'administrateur.
- Heures réelles, ETC et rétrospective : attendent les observations de l'équipe.
