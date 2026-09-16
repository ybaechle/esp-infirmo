# Backend — démonstration synthétique v0.1

FastAPI, Python 3.12, SQLAlchemy, Alembic, PostgreSQL et Redis. Le parcours T9
permet de se connecter, lire/modifier son profil puis se déconnecter. Les profils
et sessions sont persistés dans PostgreSQL. SQLite est réservé aux tests unitaires.

**Démonstration locale uniquement, données fictives exclusivement.** Ce parcours
n'est pas une authentification de production, une vérification d'identité/RPPS ou
une preuve de conformité HDS/RGPD. Aucun patient, transmission ou audio accepté.
La présence de `INFIRMO_DEMO_MODE=true` ouvre explicitement les routes `/api`;
sans cette valeur exacte, elles répondent 404. Les health checks restent disponibles.

## Lancer

Le [README racine](../README.md) décrit le lancement Docker Compose complet.
Pour développer le backend seul, fournir PostgreSQL et Redis locaux puis, depuis
`backend/`, sous PowerShell :

```powershell
uv sync --locked
$env:INFIRMO_DEMO_MODE = 'true'
$env:DATABASE_URL = 'postgresql://infirmo:local-demo-only@127.0.0.1:5432/infirmo'
$env:REDIS_URL = 'redis://127.0.0.1:6379/0'
uv run python -m alembic upgrade head
uv run python -m app.seed_demo
uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Adapter l'URL aux identifiants synthétiques de la base locale. Les migrations
créent `demo_accounts` et `demo_sessions`; le serveur ne crée jamais le schéma.
L'amorçage conserve les profils existants et ne réinitialise pas les mots de passe.
Il refuse toute adresse ne finissant pas par le domaine réservé `.example`.

| Variable | Utilisation |
| --- | --- |
| `DATABASE_URL` | URL PostgreSQL; obligatoire pour migrations et routes métier |
| `REDIS_URL` | Redis obligatoire pour disponibilité et limitation de connexion |
| `INFIRMO_DEMO_MODE` | `true` explicite; aucune activation par défaut |
| `INFIRMO_DEMO_EMAIL` | Amorçage uniquement; défaut `demo@infirmo.example` |
| `INFIRMO_DEMO_PASSWORD` | Amorçage uniquement; défaut public `Infirmo-demo-2026!`, minimum 12 caractères |

## Contrat API

| Route | Corps / résultat |
| --- | --- |
| `POST /api/auth/login` | `{ "email": "demo@infirmo.example", "password": "Infirmo-demo-2026!" }` → `{ "access_token": "…", "token_type": "bearer" }` |
| `GET /api/profile` | → `{ "display_name": "Camille Démo", "role": "remplacant", "city": "Nancy" }` |
| `PUT /api/profile` | Les trois champs du profil → profil enregistré |
| `POST /api/auth/logout` | Révoque la session courante → 204 |
| `GET /health` | Liveness → 200 |
| `GET /health/ready` | PostgreSQL et Redis → 200 ou 503 |
| `GET /metrics` | Compteurs et latences HTTP |

Les routes de profil et de déconnexion exigent `Authorization: Bearer <token>`.
`display_name` et `city` : 1 à 80 caractères imprimables après suppression des
espaces périphériques. `role` : `titulaire` ou `remplacant`; il s'agit d'un champ
professionnel, pas d'une élévation de privilèges. Les champs supplémentaires sont
refusés. Email limité à 254 caractères; mot de passe de connexion à 128.
Erreurs génériques : 401, 422, 429 (réessayer après 60 s), 503. Aucun corps invalide
n'est renvoyé dans les erreurs. Réponses métier marquées `Cache-Control: no-store`.

Les mots de passe utilisent scrypt (sel aléatoire, N=32768, r=8, p=1); vérification
en temps constant via `hmac.compare_digest`. Les jetons opaques aléatoires de
256 bits expirent après une heure; seul leur SHA-256 est conservé. Déconnexion =
suppression de la session. Les sessions expirées sont nettoyées à la connexion.
Redis autorise 30 tentatives/minute globalement, tous workers confondus; sa panne
bloque les nouvelles connexions. Cette limite convient à la démo partagée et peut
temporairement bloquer tous les démonstrateurs. Pour un service multi-utilisateur,
prévoir des limites par compte/IP et une authentification de production revue.

La démo ne fournit pas encore MFA, récupération de compte, vérification RPPS,
audit nominatif de production, chiffrement du stockage ou déploiement HDS.
Les garanties de transport/stockage nécessaires aux données réelles devront être
réalisées et vérifiées avant leur utilisation. Garder ce service sur loopback et
ne saisir que des identités fictives. Aucun journal de corps, profil ou jeton.

## Vérifier

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest -q
```

Le seuil de couverture `app` de 70 % est obligatoire dans `pyproject.toml`;
`coverage.xml` est généré. Les tests vérifient contrôle d'accès, isolation entre
comptes, persistance, expiration/révocation, validation et limitation Redis.

### Intégration PostgreSQL réelle

Avec une **base dédiée jetable** et Redis démarrés :

```powershell
$env:TEST_DATABASE_URL = 'postgresql://infirmo:local-demo-only@127.0.0.1:5432/infirmo_test'
$env:REDIS_URL = 'redis://127.0.0.1:6379/0'
uv run python -m pytest -q
```

Le test crée son propre schéma aléatoire, applique les migrations deux fois,
effectue connexion/modification, recrée les connexions DB, relit le profil,
révoque la session et teste downgrade/upgrade. Il supprime uniquement ce schéma
en sortie. Sans `TEST_DATABASE_URL`, ce test est explicitement **skipped** : une
suite SQLite verte ne prouve pas l'intégration PostgreSQL. Le script
[`infra/check_v01.py`](../infra/check_v01.py) vérifie aussi l'API HTTP de Compose.

Versionnement indépendant : `backend-vX.Y.Z`.
