# Contribuer au projet INFIRMO

Ce document décrit les règles de contribution au projet INFIRMO : organisation du dépôt, conventions Git, gestion des tickets, sprints, sécurité, documentation et Definition of Done.

Il doit rester aligné avec le cahier des charges INFIRMO v4 et avec le GitHub Project utilisé pour le suivi du backlog.

---

## 1. Organisation du dépôt

Le projet est organisé dans un dépôt principal unique : `infirmo`.

Ce dépôt sert de mono-repo pour centraliser la documentation, le code applicatif et la configuration DevOps. La structure complète sera mise en place progressivement au fur et à mesure du développement.

Structure cible du dépôt :

```text
.
├── README.md
├── CONTRIBUTING.md
├── docs/
│   └── livrables/
├── mobile/
├── backend/
├── ia/
└── infra/
```

Les dossiers `mobile/`, `backend/`, `ia/` et `infra/` correspondent aux principaux modules techniques du projet. Ils peuvent être créés progressivement lorsque les tickets associés démarrent.

Pour qu’un dossier vide soit visible dans GitHub, il doit contenir au moins un fichier, par exemple un `README.md` ou un `.gitkeep`.

La structure cible permet de garder une séparation claire entre les modules tout en conservant un dépôt unique. Ce choix simplifie Docker Compose, la configuration CI/CD, le suivi des livrables et la coordination entre les parties mobile, backend, IA et infrastructure.

---

## 2. Méthodologie de projet

Le projet suit une méthodologie **ScrumBan**.

Cette méthode combine :

- un cadre inspiré de Scrum : sprints, rituels, revues, rétrospectives ;
- la flexibilité de Kanban : adaptation continue, gestion des blocages, ajustement des priorités.

Dans le cadre du projet INFIRMO, les sprints sont utilisés comme des cycles de travail effectif. Un sprint représente environ **5 jours-hommes de travail projet par membre**.

En raison du rythme d’alternance, ces jours ne sont pas nécessairement consécutifs. Ils sont répartis sur les jours projet disponibles, principalement les vendredis pendant les périodes en entreprise. Les réunions sont regroupées autant que possible pendant les semaines école.

---

## 3. Milestones et sprints

Le projet est suivi à deux niveaux complémentaires.

Les **milestones M1 à M6** correspondent aux grands jalons fonctionnels et documentaires du projet. Ils servent à structurer la roadmap macro du cahier des charges.

Les **sprints** correspondent aux cycles opérationnels de travail. Ils servent à organiser concrètement les tickets dans GitHub Projects.

| Niveau | Usage |
| ------ | ----- |
| Milestone | Suivi macro du projet et des livrables : M1 à M6. |
| Sprint | Suivi opérationnel des tickets par cycle de travail effectif. |
| Start date / Target date | Dates utilisées pour l’affichage Roadmap dans GitHub Projects. |

Un ticket peut donc appartenir à un milestone fonctionnel tout en étant traité dans un sprint précis.

Exemple :

```text
Ticket : MOB-1 - Initialisation projet Flutter et intégration Figma
Milestone : M1
Sprint : Sprint 1
```

Le ticket reste rattaché à M1 dans le cahier des charges, mais son exécution technique démarre en septembre dans GitHub Projects.

---

## 4. Sprints de travail

Le champ `Sprint` dans GitHub Projects est un champ de type itération. Il contient les cycles opérationnels de travail.

Les sprints configurés sont les suivants :

| Sprint | Période | Objectif opérationnel |
| ------ | ------- | -------------------- |
| Sprint 1 | 11/09/2026 - 24/09/2026 | Lancement technique : structure du dépôt, conventions, setup mobile/backend/IA, Docker, CI initiale. |
| Sprint 2 | 25/09/2026 - 27/11/2026 | Développement MVP Core : authentification, profils, documents, matching, premières intégrations. |
| Sprint 3 | 30/11/2026 - 22/01/2027 | Remplacements et communication : candidatures, calendrier, messagerie, transmissions, IA. |
| Sprint 4 | 29/01/2027 - 05/03/2027 | Tests, intégration, sécurité, optimisation et stabilisation de l’application. |
| Sprint 5 | 12/03/2027 - 19/03/2027 | Clôture opérationnelle : documentation technique, passation, livraison candidate. |

Avril 2027 est une réserve de finalisation. Ce n’est pas une phase principale de développement. Cette période sert à absorber les retards éventuels, corriger les anomalies, stabiliser la démonstration et préparer la soutenance.

---

## 5. Gestion des tickets dans GitHub Projects

Les tickets GitHub Projects reprennent le backlog consolidé du cahier des charges. Ils ne doivent pas être recréés librement sans lien avec le WBS ou les user stories.

Chaque ticket doit conserver les informations suivantes :

| Champ | Usage |
| ----- | ----- |
| `Assignees` | Membre responsable du ticket. |
| `Estimation JH` | Charge estimée en jours-hommes. |
| `Priority` | Priorité native GitHub : High, Medium ou Low. |
| `Epic` | Domaine fonctionnel ou technique : auth, mobile, backend, IA, DevOps, tests, documentation, etc. |
| `WBS_Code` | Code WBS permettant la traçabilité avec le cahier des charges. |
| `WBS_Concerned` | Description du ou des lots WBS concernés. |
| `Milestone_Period` | Période macro du milestone concerné. |
| `Sprint` | Sprint opérationnel dans lequel le ticket est traité. |
| `Start date` / `Target date` | Dates utilisées pour la Roadmap GitHub Projects. |

Les milestones M1 à M6 servent au suivi macro du projet. Les sprints servent au suivi opérationnel du travail.

Les tickets transversaux, comme le suivi ScrumBan, la qualité ou les réunions projet, peuvent rester sans sprint unique lorsqu’ils couvrent toute la durée du projet.

---

## 6. Workflow des tickets

Le workflow utilisé dans GitHub Projects est :

```text
To Do → In Progress → In Review → Done
```

Signification des statuts :

| Statut | Signification |
| ------ | ------------- |
| `To Do` | Ticket prêt à être traité, mais non commencé. |
| `In Progress` | Travail en cours par le responsable du ticket. |
| `In Review` | Travail terminé côté développement, en attente de relecture, test ou validation. |
| `Done` | Ticket terminé selon la Definition of Done. |

Un ticket ne doit pas être déplacé en `Done` si les critères de validation ne sont pas remplis.

---

## 7. Labels

Les labels GitHub peuvent être utilisés comme aide visuelle, mais ils ne constituent pas le système principal de suivi du projet.

Le suivi principal se fait dans GitHub Projects à l’aide des champs :

- `Sprint`
- `Priority`
- `Epic`
- `Estimation JH`
- `WBS_Code`
- `Milestone_Period`
- `Start date`
- `Target date`

Les labels peuvent être ajoutés ponctuellement pour faciliter le tri ou signaler un type de travail.

Exemples de labels possibles :

| Label | Usage |
| ----- | ----- |
| `bug` | Correction d’un défaut ou comportement inattendu. |
| `feature` | Nouvelle fonctionnalité. |
| `improvement` | Amélioration d’un élément existant. |
| `documentation` | Documentation, README, livrables, supports de présentation. |
| `urgent` | Élément bloquant ou prioritaire. |

Les labels ne remplacent pas les champs `Epic`, `Priority`, `WBS_Code` ou `Sprint`. Ils restent optionnels et servent uniquement à faciliter la lecture visuelle du projet.

---

## 8. Conventions Git

Le projet utilise une stratégie inspirée de **Git Flow**.

Branches principales :

| Branche | Usage |
| ------- | ----- |
| `main` | Version stable / production ou démonstration validée. |
| `develop` | Branche d’intégration principale. |
| `feature/*` | Développement d’une fonctionnalité. |
| `bugfix/*` | Correction d’un bug non urgent. |
| `hotfix/*` | Correction urgente sur une version stable. |
| `docs/*` | Documentation. |
| `ci/*` | Configuration CI/CD. |
| `test/*` | Ajout ou correction de tests. |
| `refactor/*` | Refactorisation sans changement fonctionnel. |

Formats autorisés :

```text
feature/<description>
bugfix/<description>
hotfix/<description>
docs/<description>
ci/<description>
test/<description>
refactor/<description>
dev/<description>
```

Exemples :

```text
feature/auth-login
bugfix/profile-upload
docs/update-readme
ci/backend-tests
```

Les branches `main` et `develop` doivent être protégées. Toute modification doit passer par une Pull Request. La configuration de protection est versionnée dans [`infra/github/`](infra/github/README.md).

---

## 9. Pull Requests

Chaque Pull Request doit :

- être liée à un ticket GitHub Projects ;
- avoir un titre clair ;
- expliquer brièvement les changements réalisés ;
- être relue avant fusion ;
- passer les vérifications automatiques disponibles ;
- respecter la Definition of Done lorsque le ticket est finalisé.

La fusion se fait selon la règle suivante :

| Destination | Méthode de fusion |
| ----------- | ----------------- |
| `develop` | Squash merge |
| `main` | Merge commit |

---

## 10. Commits

Les messages de commit respectent la convention **Conventional Commits**.

Types autorisés :

```text
feat     ajout d’une fonctionnalité
fix      correction d’un bug
docs     documentation
style    formatage sans changement fonctionnel
refactor refactorisation
test     ajout ou correction de tests
chore    tâche technique
ci       configuration CI/CD
perf     optimisation de performance
build    build, dépendances ou packaging
```

Format :

```text
type(scope): message court
```

Exemples :

```text
feat(auth): add JWT login
fix(profile): validate uploaded document type
docs(readme): update sprint organization
ci(backend): add pytest workflow
```

Pour être guidé lors de la rédaction d’un commit, l’équipe peut utiliser :

```bash
npx git-cz
```

---

## 11. Conventions de code

### Python — backend / IA

Outils :

- Black pour le formatage ;
- Ruff pour le linting ;
- pytest pour les tests.

Conventions :

- `snake_case` pour les variables, fonctions et fichiers Python ;
- validation stricte des entrées ;
- pas de secret en clair dans le code ;
- configuration via variables d’environnement.

Commandes recommandées :

```bash
ruff check .
black .
pytest
```

### Dart / Flutter — mobile

Outils :

- `dart format` pour le formatage ;
- `flutter analyze` pour l’analyse statique ;
- `flutter test` pour les tests.

Conventions :

- `camelCase` pour les variables et méthodes ;
- `PascalCase` pour les classes et widgets ;
- séparation claire des widgets, services et modèles.

Commandes recommandées :

```bash
dart format .
flutter analyze
flutter test
```

### Base de données

Conventions :

- `lower_snake_case` pour les tables et colonnes ;
- migrations versionnées ;
- contraintes explicites lorsque nécessaire ;
- pas de données sensibles réelles dans les environnements de développement.

---

## 12. Sécurité

Les règles suivantes sont obligatoires :

- aucun secret en clair dans le dépôt ;
- utilisation d’un fichier `.env.example` sans valeur sensible ;
- variables d’environnement pour les secrets ;
- validation systématique des entrées utilisateur ;
- séparation des droits selon les rôles ;
- attention particulière aux données de santé et aux informations personnelles ;
- chiffrement des échanges en HTTPS/TLS ;
- journalisation des accès sensibles lorsque nécessaire.

Tout fichier contenant des secrets doit être supprimé de l’historique si une fuite est détectée.

---

## 13. Documentation

La documentation doit être maintenue au fil du projet.

Éléments attendus :

| Élément | Emplacement |
| ------- | ----------- |
| README principal | Racine du dépôt |
| Conventions projet | `CONTRIBUTING.md` |
| Documentation mobile | `mobile/README.md` |
| Documentation backend | `backend/README.md` |
| Documentation IA | `ia/README.md` |
| Documentation infra | `infra/README.md` |
| Cahier des charges | `docs/livrables/` |
| Documentation API | Swagger / OpenAPI |

Les README de module peuvent être créés progressivement lorsque les dossiers correspondants sont initialisés.

La documentation doit être mise à jour lorsqu’une fonctionnalité, une commande ou une configuration change.

---

## 14. Definition of Done

Une contribution est considérée comme terminée uniquement lorsque les critères suivants sont remplis :

- [ ] Le code est développé et relu via Pull Request.
- [ ] Le ticket GitHub Projects est à jour.
- [ ] Les critères d’acceptation du ticket sont validés.
- [ ] Les tests automatisés passent lorsque le ticket est concerné.
- [ ] La CI est verte lorsque la CI est disponible.
- [ ] Aucune régression critique n’est introduite.
- [ ] Les règles de sécurité sont respectées.
- [ ] Aucun secret n’est présent dans le code.
- [ ] La documentation est mise à jour si nécessaire.
- [ ] La fonctionnalité est validée en environnement de recette ou démontrée si applicable.

Un ticket ne doit être déplacé en `Done` que lorsque cette Definition of Done est respectée.

---

## 15. Gestion des réunions

Les réunions sont comptabilisées dans la charge projet.

Le cahier des charges prévoit, par membre :

```text
5 réunions longues de 1h = 5h
16 points courts de 15 min = 4h
Total réunions = 9h ≈ 1,3 JH
```

La charge totale par membre est donc :

```text
21 JH total
19,7 JH productifs
1,3 JH réunions / coordination
```

Les réunions longues servent aux revues de sprint, à la planification et aux arbitrages. Les points courts servent au suivi, à la remontée des blocages et à la mise à jour du projet.

---

## 16. Bonnes pratiques attendues

Chaque membre de l’équipe doit :

- consulter GitHub Projects avant de commencer une tâche ;
- travailler sur une branche dédiée ;
- lier son travail au ticket correspondant ;
- demander une relecture avant fusion ;
- signaler rapidement les blocages ;
- maintenir la documentation à jour ;
- respecter les conventions de code et de sécurité ;
- éviter les changements hors périmètre non validés.

---

## 17. Références

- Cahier des charges INFIRMO v4
- GitHub Projects du projet INFIRMO
- README principal du dépôt
- Definition of Done du projet
