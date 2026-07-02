# infra/deploy/ — staging & production (INF-12, INF-13, INF-14)

Runbook de déploiement pour l'environnement **staging** (hébergement Docker
non-HDS, données **synthétiques uniquement**) et pour le **déploiement
production** (tags `semantic-release`), avec sa procédure de **rollback**.

> Rappel obligation légale : voir [`../hds/README.md`](../hds/README.md) et
> AGENTS.md §5. Aucune donnée de santé réelle sur l'environnement staging.

## 1. Architecture staging

```text
                        Internet (80/443)
                              │
                              ▼
                        ┌───────────┐
                        │   caddy   │  TLS automatique (Let's Encrypt)
                        │ (publié)  │
                        └─────┬─────┘
                              │ réseau "default"
                              ▼
                        ┌───────────┐        ┌───────────┐
                        │  backend  │◄──────►│    db     │
                        │ (FastAPI) │        │ (Postgis) │
                        └─────┬─────┘        └───────────┘
                              │ réseau "internal"   ▲
                              ▼                     │ réseau "default"
                        ┌───────────┐        ┌───────────┐
                        │    ia     │        │   redis   │
                        │ (Whisper) │        └───────────┘
                        └───────────┘
```

Seul `caddy` est publié sur l'hôte (80/443). `backend` n'est joignable que
via `caddy` ; `ia` n'est joignable que depuis `backend`, sur le réseau
interne `internal` (non routable vers l'extérieur) — mêmes frontières que le
`docker-compose.yml` de dev local (voir `project-architecture`).

`backend` et `ia` sont des **images publiées sur GHCR**, jamais construites
sur le serveur (`image:`, pas `build:`) — voir §3.

## 2. Premier déploiement d'un serveur

Prérequis sur le serveur cible :

- Docker + le plugin `docker compose` (v2) installés.
- Un utilisateur SSH dédié au déploiement (clé publique autorisée, pas de mot
  de passe).
- Le DNS de `STAGING_DOMAIN` pointe déjà vers le serveur (nécessaire pour que
  Caddy obtienne un certificat TLS automatiquement).

Étapes :

```bash
# 1. Créer le dossier de déploiement.
mkdir -p ~/infirmo

# 2. Copier docker-compose.staging.yml et Caddyfile sur le serveur, dans
#    ~/infirmo/ (scp, ou un clone git peu profond du dépôt).
scp infra/deploy/docker-compose.staging.yml infra/deploy/Caddyfile \
    <user>@<host>:~/infirmo/

# 3. Copier le fichier d'exemple sous le nom ".env" (docker compose charge
#    automatiquement le ".env" situé à côté du fichier compose utilisé avec
#    -f — voir la doc Docker Compose sur le "project directory").
cp infra/deploy/.env.staging.example ~/infirmo/.env
# puis éditer ~/infirmo/.env sur le serveur : POSTGRES_PASSWORD,
# BACKEND_IMAGE, IA_IMAGE, STAGING_DOMAIN. Ne jamais committer ce fichier.

# 4. Premier démarrage.
cd ~/infirmo
docker compose -f docker-compose.staging.yml pull
docker compose -f docker-compose.staging.yml up -d

# 5. Vérifier.
curl https://<STAGING_DOMAIN>/health
```

## 3. Déploiement automatique staging (INF-13)

Workflow : [`deploy-staging.yml`](../../.github/workflows/deploy-staging.yml).

1. Un push sur `develop` qui touche `backend/**`, `ia/**`, `infra/deploy/**`
   (ou le workflow lui-même) déclenche le job **build-push** : build des
   images `backend` et `ia`, publication sur GHCR taguées `develop` et
   `sha-<sha-court>`.
2. Le job **deploy** se connecte en SSH au serveur staging et exécute
   `docker compose -f ~/infirmo/docker-compose.staging.yml pull` puis
   `up -d` : les conteneurs redémarrent avec les images `:develop`
   fraîchement publiées (référencées par `BACKEND_IMAGE`/`IA_IMAGE` dans
   `~/infirmo/.env`).
3. `workflow_dispatch` permet de rejouer le déploiement manuellement.
4. Une pull request qui touche uniquement `deploy-staging.yml` déclenche à la
   place **build-validation** : les images sont construites (pas publiées)
   pour donner un check vert sans droits d'écriture sur le registre.

Si les secrets SSH (§6) ne sont pas configurés, le job **deploy** affiche un
`::notice::` et se termine proprement (`exit 0`) — le pipeline reste vert
tant qu'aucun serveur staging n'est encore provisionné.

## 4. Déploiement production (INF-14)

Workflow : [`deploy-production.yml`](../../.github/workflows/deploy-production.yml).

La production se déclenche sur les tags `backend-vX.Y.Z` / `ia-vX.Y.Z` créés
par `semantic-release` (voir `release.yml`, déclenché par un push sur
`main`) :

1. Le push du tag construit l'image du module concerné et la publie sur GHCR
   avec le tag exact de version (`vX.Y.Z`, immuable).
2. Le job se connecte en SSH au serveur de production et exécute, pour le
   seul module concerné :
   `docker compose -f ~/infirmo/docker-compose.staging.yml pull <module>`
   puis `up -d <module>` — l'autre module n'est pas touché.

`BACKEND_IMAGE` (ou `IA_IMAGE`) est exporté avec la version pinnée
uniquement pour cette invocation SSH ; le `.env` persistant sur le serveur
n'a pas besoin d'être réécrit à chaque déploiement.

> Le même fichier compose sert pour staging et pour un futur serveur de
> production/HDS (voir [`../hds/README.md`](../hds/README.md) §4) : seul le
> contenu de `.env` et l'hébergeur diffèrent entre les deux.

## 5. Procédure de rollback

Les images GHCR sont **immuables** : "rollback" = redéployer une version
antérieure déjà publiée, pas reconstruire quoi que ce soit.

1. Retrouver la version précédente du module concerné :

   ```bash
   git tag -l 'backend-v*' | sort -V
   # ou pour ia :
   git tag -l 'ia-v*' | sort -V
   ```

   La version à redéployer est celle qui précède la version actuellement en
   production dans cette liste triée.

2. Aller sur **Actions → Deploy Production → Run workflow**
   (`workflow_dispatch`).
3. Renseigner :
   - `module` : `backend` ou `ia` ;
   - `version` : la version antérieure identifiée à l'étape 1, ex. `v1.2.2`.
4. Lancer le workflow. Comme l'événement est `workflow_dispatch` (pas un
   push de tag), **aucun build n'est déclenché** : le workflow tire
   directement `ghcr.io/<repo>/<module>:v1.2.2` (déjà publiée) et
   redémarre le seul conteneur `<module>` avec cette image.
5. Vérifier `curl https://<domaine-production>/health` puis surveiller les
   logs/métriques (sans donnée de santé — voir AGENTS.md §5.6).

## 6. Secrets GitHub à configurer

À définir dans **Settings → Secrets and variables → Actions** du dépôt.
Tant qu'un environnement n'a pas de serveur provisionné, laisser ses secrets
vides : les workflows sautent proprement le déploiement (§3).

| Secret | Environnement | Contenu |
| ------ | -------------- | ------- |
| `STAGING_SSH_HOST` | staging | Adresse (IP ou domaine) du serveur staging |
| `STAGING_SSH_USER` | staging | Utilisateur SSH de déploiement |
| `STAGING_SSH_KEY` | staging | Clé privée SSH dédiée (jamais réutilisée ailleurs) |
| `PROD_SSH_HOST` | production | Adresse du serveur de production |
| `PROD_SSH_USER` | production | Utilisateur SSH de déploiement |
| `PROD_SSH_KEY` | production | Clé privée SSH dédiée |

`GITHUB_TOKEN` (publication sur GHCR) est fourni automatiquement par
GitHub Actions — pas de secret à créer pour ça.

## 7. Rappel synthétique / HDS

L'environnement **staging** décrit ici est un hébergement Docker **non
certifié HDS** : **données synthétiques uniquement**, aucune donnée de santé
réelle (AGENTS.md §5). La cible d'hébergement certifiée HDS, la checklist de
migration et le périmètre concerné sont documentés dans
[`../hds/README.md`](../hds/README.md).
