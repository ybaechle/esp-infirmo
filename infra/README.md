# infra/

Infrastructure-as-code, container images, and deployment manifests for Infirmo.

## Stack

- **IaC:** Terraform (cloud provider TBD)
- **Local dev:** Docker / Docker Compose
- **Orchestration:** Kubernetes (manifests + Helm charts as workloads grow)

This README is a placeholder for the Terraform/Kubernetes parts. Module layout (`terraform/<env>/`, `k8s/`, `charts/`) will be filled in by later infra tickets. The local Docker Compose setup (below) was delivered by **INF-8**; staging/production deployment (Docker Compose + GitHub Actions, no Kubernetes yet) was delivered by **INF-12/13/14** — see [`infra/deploy/`](deploy/README.md).

## Démarrage local (Docker Compose)

Environnement de développement local uniquement — **données synthétiques
uniquement**, ce n'est pas l'environnement HDS (voir la skill `hds-hosting`
et AGENTS.md §5). Cette section reste volontairement minimale ; les
environnements staging/production sont documentés dans la section
"Environnements" ci-dessous. Monitoring et backups arrivent avec **INF-18**.

### Prérequis

- Docker et Docker Compose (plugin `docker compose`, v2).

### Démarrer

```bash
# 1. Copier le fichier d'exemple et renseigner un mot de passe local.
#    .env est ignoré par git : ne jamais y mettre de vraies valeurs.
cp .env.example .env

# 2. Construire les images et démarrer les services (db, redis, backend, ia).
docker compose up -d --build

# 3. Vérifier que le backend répond (liveness).
curl http://localhost:8000/health

# 4. Arrêter et retirer les conteneurs.
docker compose down
```

### Services

| Service | Rôle | Exposé sur l'hôte |
| ------- | ---- | ------------------ |
| `db` | PostgreSQL + PostGIS 16 | Non (voir `docker-compose.yml` pour activer ponctuellement) |
| `redis` | Redis 7 (pub/sub, cache) | Non |
| `backend` | API FastAPI (scaffold DevOps, INF-8) | `8000` |
| `ia` | Microservice IA (scaffold, sans Whisper) | Non — appelable uniquement par `backend`, réseau `internal` |

`backend/` et `ia/` sont pour l'instant des **scaffolds DevOps minimaux**
(healthchecks uniquement) : ils seront remplacés par le code applicatif réel
des équipes backend et IA.

## Environnements

| Environnement | Hébergement | Données | Documentation |
| -------------- | ----------- | ------- | -------------- |
| Local | `docker compose` sur la machine du développeur | Synthétiques | Ce fichier (§ "Démarrage local") |
| Staging | Serveur Docker "nu", non-HDS (déploiement auto depuis `develop`) | **Synthétiques uniquement** | [`infra/deploy/`](deploy/README.md) |
| Production — cible HDS | Hébergeur certifié HDS (OVHcloud recommandé), déploiement depuis les tags `semantic-release` | Réelles (une fois l'hébergement HDS contractualisé) | [`infra/hds/`](hds/README.md) (POC/cible) · [`infra/deploy/`](deploy/README.md) (pipeline) |

Aucune donnée de santé réelle ne doit transiter par les environnements local
ou staging (AGENTS.md §5, skill `hds-hosting`).

## Owner(s)

- TBD

## Notes

- State files (`*.tfstate`) and variable files (`*.tfvars`) are ignored — commit `*.tfvars.example` instead.
- Local `docker-compose.override.yml` is ignored to allow per-developer tweaks.
- `kubeconfig` and `secrets/` are ignored — use a secret manager (Vault / SOPS / cloud-native) rather than committing secrets.

## Versioning

Versioned alongside the package(s) being deployed. There is no separate `infra-v*` tag.
