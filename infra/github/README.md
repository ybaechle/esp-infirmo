# Organisation GitHub — INFIRMO

Configuration GitHub du projet : organisation, dépôt, protection des branches.
Couvre les tickets **INF-1** (organisation et dépôts) et **INF-2** (protection
des branches).

## Organisation et dépôt (INF-1)

| Élément | Valeur |
| ------- | ------ |
| Organisation | `EpitechMscProPromo2027` |
| Dépôt | `T-ESP-901-NCY-9-1-T-ESP-901-1` |
| Visibilité | Privé |
| Branche par défaut | `main` |
| Suivi du backlog | GitHub Projects (champs `Sprint`, `Priority`, `Epic`, `WBS_Code`…) |

Le projet est un **mono-repo** : `mobile/`, `backend/`, `ia/` et `infra/` vivent
dans le même dépôt, chacun versionné indépendamment (`<module>-vX.Y.Z`).
La justification du choix mono-repo et l'organisation des tickets sont décrites
dans [`CONTRIBUTING.md`](../../CONTRIBUTING.md) (§1 et §5).

Branches permanentes :

| Branche | Rôle |
| ------- | ---- |
| `main` | Version stable / démonstration validée. Fusion par merge commit. |
| `develop` | Intégration continue du travail d'équipe. Fusion par squash. |

## Protection des branches (INF-2)

La configuration est versionnée sous forme de **rulesets** GitHub dans
[`rulesets/`](rulesets/) :

| Fichier | Cible | Règles |
| ------- | ----- | ------ |
| `branch-main.json` | `main` | PR obligatoire, 1 relecture, pas de force-push ni suppression, merge commit uniquement |
| `branch-develop.json` | `develop` | PR obligatoire, 1 relecture, pas de force-push ni suppression, squash uniquement |

### Appliquer les rulesets

> ⚠️ Nécessite le rôle **admin** sur le dépôt (rôle organisation Epitech).
> Les membres de l'équipe ont un accès `write` : demander l'application à un
> administrateur de l'organisation.

Via l'interface : **Settings → Rules → Rulesets → New ruleset → Import a ruleset**,
puis importer chaque fichier JSON de `rulesets/`.

Via l'API :

```bash
REPO=EpitechMscProPromo2027/T-ESP-901-NCY-9-1-T-ESP-901-1
gh api "repos/$REPO/rulesets" --method POST --input infra/github/rulesets/branch-main.json
gh api "repos/$REPO/rulesets" --method POST --input infra/github/rulesets/branch-develop.json
```

## Commits et releases (INF-4 → INF-6)

- **Commitlint** : chaque commit et chaque titre de PR respectent les
  Conventional Commits (`commitlint.config.js`, workflow
  `.github/workflows/commitlint.yml`). Le hook local s'installe avec
  `npm install` à la racine (script `prepare` → `.githooks/commit-msg`).
- **Commits guidés** : `npm run commit` (ou `npx git-cz`) pose les questions
  et construit un message conforme.
- **semantic-release** : à chaque push sur `main`, le workflow
  `.github/workflows/release.yml` calcule la prochaine version de chaque
  module depuis l'historique de commits et publie tags + releases GitHub
  au format `<module>-vX.Y.Z` (`backend/.releaserc.json`, etc. — les
  `package.json` de module sont des manifestes de release, pas du code).

## Quality checks

`quality.yml` runs on all PRs and all `develop`/`main` pushes. Reusable workflows
validate backend, IA and mobile. The cold-start job builds the complete Compose
stack and runs `infra/check_v01.py`. The stable **Quality gate** requires all four
results to be `success`, including when a dependency fails or is skipped.

Backend/IA: Ruff, pytest, coverage >=70%, XML/JUnit reports. Mobile: formatting,
analysis, tests with LCOV and web build. Report figures with SHA and date in
`/reporting/`. Missing Actions budget is an execution blocker, not a test result.

The versioned rulesets require `Quality gate`. An administrator must still apply
them using the commands above and verify active remote rules. JSON files alone
do not protect branches. Update existing rulesets by ID rather than duplicating.
These quality checks have no path filters that could leave PRs pending.

## Deployment

Staging follows a successful Quality push run on `develop`. Release validates the
quality suite on `main`, then explicitly dispatches each new module tag to Deploy
Production. See [deployment](../deploy/README.md) for secrets, persisted versions,
readiness, acceptance and rollback.
