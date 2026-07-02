# Organisation GitHub — INFIRMO

Configuration GitHub du projet : organisation, dépôt, protection des branches.
Couvre les tickets **INF-1** (organisation et dépôts) et **INF-2** (protection
des branches).

## Organisation et dépôt (INF-1)

| Élément | Valeur |
| ------- | ------ |
| Organisation | `EpitechMscProPromo2027` |
| Dépôt | `T-ESP-800-project-100856-NCY_Infirmo` |
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
REPO=EpitechMscProPromo2027/T-ESP-800-project-100856-NCY_Infirmo
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

## Intégration continue (INF-9 → INF-11)

| Workflow | Fichier | Déclencheur | Contenu |
| -------- | ------- | ----------- | ------- |
| Commitlint | `commitlint.yml` | toute PR | commits + titre de PR conventionnels |
| Backend CI | `backend-ci.yml` | changements `backend/**` | `ruff check` + `ruff format --check` + `pytest` (uv, lockfile) |
| IA CI | `ia-ci.yml` | changements `ia/**` | idem backend |
| Mobile CI | `mobile-ci.yml` | changements `mobile/**` | `dart format` + `flutter analyze` + `flutter test` (no-op vert tant que l'app Flutter n'est pas initialisée) |
| Release | `release.yml` | push `main` | semantic-release par module |

Les CI de module sont filtrées par chemin : elles ne tournent que quand le
module change (plus leur propre fichier de workflow).

### Évolutions prévues

- Ajouter les **status checks requis** (CI backend / mobile / IA / commitlint)
  dans les rulesets une fois les noms de checks stabilisés — voir
  `.github/workflows/`. Ne pas exiger un check filtré par chemin : une PR qui ne
  déclenche pas le workflow resterait bloquée.
