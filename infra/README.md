# infra/ — Documentation DevOps INFIRMO

Infrastructure, CI/CD et hébergement du projet INFIRMO (INF-18).
Ce fichier est le **point d'entrée** de toute la documentation DevOps : chaque
sous-dossier a son propre README détaillé.

Owner : **Lazaro Marrero Rousse** (DevOps) — voir AGENTS.md §1.

## Carte des livrables DevOps

| Domaine | Tickets | Où |
| ------- | ------- | -- |
| Organisation GitHub, protection des branches | INF-1, INF-2 | [`infra/github/`](github/README.md) |
| Conventions Git, commits, releases | INF-3 → INF-6 | [`CONTRIBUTING.md`](../CONTRIBUTING.md) · [`infra/github/`](github/README.md) |
| Templates issues / PR avec DoD | INF-7 | [`.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE/) · [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md) |
| Stack locale Docker Compose | INF-8 | ce fichier (§ Démarrage local) · [`docker-compose.yml`](../docker-compose.yml) |
| CI backend / mobile / IA | INF-9 → INF-11 | [`.github/workflows/`](../.github/workflows/) · [`infra/github/`](github/README.md) |
| Staging + POC HDS | INF-12 | [`infra/deploy/`](deploy/README.md) · [`infra/hds/`](hds/README.md) |
| Déploiement auto staging, production + rollback | INF-13, INF-14 | [`infra/deploy/`](deploy/README.md) |
| Monitoring Prometheus/Grafana | INF-15 | [`infra/monitoring/`](monitoring/README.md) |
| Sauvegardes PostgreSQL | INF-16 | [`infra/backup/`](backup/README.md) |
| Tests de performance k6 | INF-17 | [`infra/perf/`](perf/README.md) |

Terraform et Kubernetes (voir AGENTS.md §3) ne sont **pas encore utilisés** :
ils arriveront si le besoin le justifie (contractualisation HDS, montée en
charge). L'hébergement actuel est 100 % Docker Compose.

## Démarrage local (Docker Compose)

Environnement de développement local uniquement — **données synthétiques
uniquement**, ce n'est pas l'environnement HDS (AGENTS.md §5,
[`infra/hds/`](hds/README.md)).

Prérequis : Docker + plugin `docker compose` (v2).

```bash
# 1. Copier le fichier d'exemple et renseigner un mot de passe local.
#    .env est ignoré par git : ne jamais y mettre de vraies valeurs.
cp .env.example .env

# 2. Construire les images et démarrer les services (db, redis, backend, ia).
docker compose up -d --build

# 3. Vérifier que le backend répond.
curl http://localhost:8000/health         # liveness
curl http://localhost:8000/health/ready   # readiness (Postgres + Redis réels)

# 4. Arrêter et retirer les conteneurs.
docker compose down
```

Le port hôte du backend est configurable (`BACKEND_PORT` dans `.env`, défaut
8000) si un autre projet occupe déjà le port.

### Services

| Service | Rôle | Exposé sur l'hôte |
| ------- | ---- | ------------------ |
| `db` | PostgreSQL + PostGIS 16 | Non (activable ponctuellement, voir `docker-compose.yml`) |
| `redis` | Redis 7 (pub/sub, cache) | Non |
| `backend` | API FastAPI (scaffold DevOps, INF-8) — expose `/metrics` (INF-15) | `${BACKEND_PORT:-8000}` |
| `ia` | Microservice IA (scaffold, sans Whisper) | Non — appelable uniquement par `backend`, réseau `internal` |
| `prometheus` / `grafana` | Profil `monitoring` (INF-15), optionnel | `9090` / `3001` (configurables) |

`backend/` et `ia/` sont pour l'instant des **scaffolds DevOps minimaux**
(healthchecks uniquement) : ils seront remplacés par le code applicatif réel
des équipes backend et IA.

## Environnements

| Environnement | Hébergement | Données | Documentation |
| -------------- | ----------- | ------- | -------------- |
| Local | `docker compose` sur la machine du développeur | Synthétiques | Ce fichier |
| Staging | Serveur Docker « nu », non-HDS (déploiement auto depuis `develop`) | **Synthétiques uniquement** | [`infra/deploy/`](deploy/README.md) |
| Production — cible HDS | Hébergeur certifié HDS (OVHcloud recommandé), déploiement depuis les tags semantic-release | Réelles (une fois l'hébergement HDS contractualisé + DPA signé) | [`infra/hds/`](hds/README.md) · [`infra/deploy/`](deploy/README.md) |

Aucune donnée de santé réelle ne doit transiter par les environnements local
ou staging : c'est une obligation légale (Art. L.1111-8 CSP), pas une
préférence — voir [`infra/hds/README.md`](hds/README.md).

## CI/CD (GitHub Actions)

Le détail des workflows (déclencheurs, contenu) est documenté dans
[`infra/github/README.md`](github/README.md). En résumé :

- **Commitlint** sur chaque PR (commits + titre) ;
- **Backend CI / IA CI / Mobile CI** filtrées par chemin (ruff + pytest via
  uv ; flutter analyze/test, no-op tant que `mobile/` n'est pas initialisé) ;
- **Release** : semantic-release publie les tags `<module>-vX.Y.Z` sur `main` ;
- **Deploy Staging** : push `develop` → images GHCR → SSH (sauté tant que les
  secrets ne sont pas configurés) ;
- **Deploy Production** : tag de release → déploiement pinné ; rollback =
  redéploiement d'une version antérieure (voir
  [`infra/deploy/README.md`](deploy/README.md)).

## Opérations

| Sujet | Ticket | Portée | Documentation |
| ----- | ------ | ------ | -------------- |
| Monitoring (Prometheus + Grafana) | INF-15 | Profil `docker compose --profile monitoring` — métriques techniques uniquement, jamais de PHI | [`infra/monitoring/`](monitoring/README.md) |
| Sauvegardes PostgreSQL | INF-16 | `backup.sh` / `restore.sh`, rotation — activité HDS n°6 pour les vraies données | [`infra/backup/`](backup/README.md) |
| Tests de performance (k6) | INF-17 | Smoke test `/health` — uniquement contre des environnements à données synthétiques | [`infra/perf/`](perf/README.md) |

## Secrets et fichiers ignorés

- Aucun secret dans le dépôt : `.env`, `*.tfvars`, `kubeconfig`, `secrets/`
  sont ignorés — committer des `*.example` à la place.
- Les secrets de déploiement (SSH staging/production) vivent dans **GitHub
  Secrets** — tableau complet dans [`infra/deploy/README.md`](deploy/README.md).
- `docker-compose.override.yml` est ignoré pour les ajustements locaux.

## Versionnement

`infra/` est versionné avec ce qu'il déploie : il n'y a **pas** de tag
`infra-v*` (voir AGENTS.md §2). Les modules applicatifs sont relâchés en
`<module>-vX.Y.Z` par semantic-release.
