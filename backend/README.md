# Backend INFIRMO

FastAPI, Python 3.12, SQLAlchemy, Alembic, PostgreSQL/PostGIS et Redis. Deux surfaces coexistent :

- **API v1** (`/api/v1`) : inscription, profils, cabinets, offres, matching, candidatures, missions,
  messagerie, transmissions patients, documents, notifications, WebSocket, audit, RGPD. Contrat :
  [`docs/api/openapi.json`](../docs/api/openapi.json), guide : [`docs/api/integration-guide.md`](../docs/api/integration-guide.md),
  décisions : [ADR 0005](../docs/adr/0005-backend-api-v1.md).
- **Démonstration v0.1** (`/api/auth/login`, `/api/profile`, `/api/auth/logout`) : parcours synthétique
  utilisé par le mobile et `infra/check_v01.py`, décrit plus bas. Elle n'est ouverte que si
  `INFIRMO_DEMO_MODE=true`.

**Données synthétiques uniquement** tant que l'hébergement HDS n'est pas validé (`AGENTS.md`).

## Configuration de l'API v1

| Variable | Rôle |
| --- | --- |
| `DATABASE_URL` | PostgreSQL **avec PostGIS** ; l'extension est créée par migration |
| `REDIS_URL` | Limitation de débit et diffusion temps réel ; sans Redis les connexions sont refusées (503) |
| `INFIRMO_ENCRYPTION_KEYS` | Trousseau AES-256 `id:base64,id:base64` (voir `.env.example`). Absent : les écritures chiffrées répondent 503 |
| `INFIRMO_STORAGE_DIR` | Dossier des fichiers chiffrés (documents, photos, vocaux) ; un volume en Compose |
| `INFIRMO_IA_URL` | Service de transcription (`POST /transcribe`). Absent : le vocal est gardé, transcription « indisponible » |

Non branchés, par choix (`AGENTS.md` : revue de résidence des données avant tout fournisseur) : e-mail/SMS de la 2FA,
push FCM/APNs, API publique de l'Ordre. Les routes concernées répondent explicitement 503 ou utilisent un mock.

Générer une clé de chiffrement et la **sauvegarder séparément de la base** (clé perdue = données illisibles) :

```sh
python -c "import base64,os;print('k1:'+base64.b64encode(os.urandom(32)).decode())"
```

## Organisation

```text
app/main.py        application, gestionnaires d'erreurs, /health, /metrics, démo
app/api/v1/        routes par domaine (auth, offices, offers, matching, applications, missions,
                   messages, patients, documents, notifications, ws, account, admin)
app/services/      règles métier : sessions, OTP, matching, missions, notifications, audit, purge, IA
app/models/        modèles SQLAlchemy ; migrations/versions/ pour le schéma
app/crypto.py      AES-256-GCM et colonne chiffrée ; app/storage.py : fichiers chiffrés
```

## Commandes d'exploitation

```sh
uv run python -m alembic upgrade head          # schéma (le serveur ne le crée jamais)
uv run python -m app.promote_admin <email>     # désigne un administrateur (compte existant)
uv run python -m app.purge                     # rétention : transmissions 30 j, sessions, défis 2FA, audit > 1 an
uv run python -m app.export_openapi            # régénère docs/api/openapi.json
```

`app.purge` doit être **planifiée** (cron ou tâche Compose, quotidienne) : aucune requête ne la déclenche.
Sans elle, les transmissions expirées restent invisibles à la lecture mais subsistent en base.

## Démonstration v0.1

**Démonstration locale uniquement, données fictives exclusivement.** Ce parcours n'est pas une authentification
de production, une vérification d'identité/RPPS ni une preuve de conformité HDS/RGPD : l'API v1 la remplace.
La présence de `INFIRMO_DEMO_MODE=true` ouvre explicitement ses routes `/api` ; sans cette valeur exacte,
elles répondent 404. Les health checks restent disponibles.

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

## Contrat de la démonstration

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

## Tests de l'API v1

```sh
export TEST_DATABASE_URL=postgresql://infirmo:local-demo-only@127.0.0.1:5432/infirmo_test
export REDIS_URL=redis://127.0.0.1:6379/0
uv run pytest -q                                   # SQLite en mémoire + tests PostgreSQL/Redis
INFIRMO_TEST_DATABASE=postgres uv run pytest -q    # toute la suite sur PostgreSQL/PostGIS
```

Sans `TEST_DATABASE_URL`, les tests qui exigent PostgreSQL (recherche géographique, parcours complet,
triggers d'audit, concurrence) sont **ignorés** et le rapport le dit : une suite SQLite verte ne les remplace pas.
Les tests WebSocket exigent `REDIS_URL`. La CI exécute les deux modes. Le contrat `openapi.json` est
comparé au code : après un changement de route, lancer `uv run python -m app.export_openapi`.

## Limites connues

- Chiffrement **au repos** côté serveur ; le chiffrement de bout en bout du cahier des charges (F4.1) n'est pas livré.
- Matching : classement sur les 300 offres les plus proches, pondérations fixes à calibrer.
- Un compte est actif dès l'inscription (numéro d'Ordre simulé, pas de vérification de l'e-mail faute de fournisseur).
- Le contrat du service IA (`POST /transcribe`) est une hypothèse à confirmer avec son responsable.
