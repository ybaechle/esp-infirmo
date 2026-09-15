# INFIRMO — incrément v0.1 / T9 BUILD

**Parcours livré : connexion avec un compte fictif, modification du profil, sauvegarde PostgreSQL et récupération après reconnexion.** Le service IA reste un squelette de santé; la transcription, l'inscription professionnelle, la 2FA, le matching et les remplacements restent au backlog.

Cette version est réservée aux **données synthétiques**. Elle ne doit recevoir aucun dossier patient ni donnée de professionnel réel. La validation HDS/production n'est pas acquise.

- [État des preuves et résultats](reporting/evidence/verification.md)
- [Tableau de bord du sprint](reporting/dashboard.md)
- [Bilan, roadmap et actions](reporting/sprint-1.md)
- [Décisions d'architecture](docs/adr/README.md)

## Installation à froid v0.1

Prérequis : Git, Docker Desktop démarré avec moteur Linux (ou Docker Engine sous Linux), plugin Compose v2 avec `--wait`, Python 3.12+ pour le contrôle d'acceptation, accès réseau aux registres de dépendances/images et accès en lecture à ce dépôt privé. Le SDK Flutter n'est pas nécessaire pour le parcours Docker. Le premier build télécharge le SDK et les dépendances : inclure ce temps dans la mesure. Vérifier `docker info`, `docker compose version` et `python --version` avant le chronomètre d'exécution; consigner séparément le temps d'installation des prérequis.

Les étapes numérotées suivantes constituent les **7 actions de référence** du protocole. Les commandes internes d'une étape ne sont pas recomptées séparément. Geler le commit et ce document avant toute tentative; consigner tout ajustement non prescrit dans le [Delta Log](reporting/delta-log.csv).

1. **Cloner la branche de livraison**, puis relever la révision. Les commandes fonctionnent dans PowerShell et dans un shell Linux/macOS.

   ```bash
   git clone --branch feature/t9-executable-reporting --single-branch https://github.com/EpitechMscProPromo2027/T-ESP-901-NCY-9-1-T-ESP-901-1.git infirmo
   cd infirmo
   git rev-parse HEAD
   ```

2. **Créer la configuration locale**, uniquement dans ce clone neuf.

   ```bash
   cp .env.example .env
   ```

   Les identifiants d'exemple sont fictifs et réservés à cet environnement local. Ne jamais écraser un `.env` existant. Si un port est occupé, configurer `WEB_PORT`/`BACKEND_PORT` dans `.env` et utiliser ce port dans les étapes suivantes; cette option fait partie de la procédure.

3. **Valider la configuration.**

   ```bash
   docker compose config --quiet
   ```

   Résultat attendu : code de sortie 0. Ne pas ajouter de clés manuellement pour contourner une erreur : corriger `.env.example` et tracer une nouvelle tentative.

4. **Construire et démarrer** les services. Les migrations et le compte fictif sont initialisés par la procédure versionnée.

   ```bash
   docker compose up -d --build --wait --wait-timeout 300
   docker compose ps
   ```

   Résultat attendu : les services nécessaires démarrent et les contrôles de santé passent. Le compte initial est `demo@infirmo.example`, mot de passe `Infirmo-demo-2026!`. Il est créé uniquement avec le mode de démonstration explicitement activé.

5. **Exécuter le contrôle d'acceptation API.**

   ```bash
   python infra/check_v01.py --url http://localhost:8080
   ```

   Résultat attendu : code de sortie 0 après connexion, écriture/relecture persistante et révocation de session. Le contrôle utilise seulement le compte fictif; consulter son `--help` si les paramètres de démonstration ont été personnalisés.

6. **Valider le parcours interface** dans `http://localhost:8080` (ou le `WEB_PORT` configuré) : se connecter, modifier le nom fictif/la ville/le rôle, enregistrer, se déconnecter puis se reconnecter. Vérifier les valeurs sauvegardées. Recharger l'onglet et se reconnecter : la session n'est pas conservée sur l'appareil, le profil reste dans PostgreSQL.

7. **Arrêter et vérifier la conservation des données.**

   ```bash
   docker compose down
   docker compose up -d --wait --wait-timeout 300
   ```

   Refaire la connexion et vérifier le profil, puis `docker compose down`. Ne pas ajouter `--volumes` : cela supprimerait les données de ce projet. Noter fin, durée, résultat, écarts et révision dans [le protocole indépendant](reporting/onboarding.md).

### Tests de développement

Les commandes propres à chaque module sont décrites dans [backend](backend/README.md), [mobile](mobile/README.md) et [IA](ia/README.md). Flutter 3.44.0 est utilisé pour le mobile; le build web distribue la même application pour l'exercice externe. Un build Android nécessite en plus le SDK Android décrit dans le README mobile.

```bash
python -m unittest discover -s reporting -p "test_*.py"
python reporting/dashboard.py
```

Pour une répétition locale isolée, les mêmes commandes Compose peuvent recevoir `--env-file .env.example -p infirmo-t9-check`; changer les ports si une autre instance fonctionne. Cette répétition ne constitue pas la validation par un pair sur machine propre.

---

## Cadrage du projet

**Le réseau professionnel des infirmiers libéraux**

INFIRMO est un projet réalisé dans le cadre du module **T-ESP-800 — Epitech Nancy, MSC 2027**.

Le projet vise à concevoir une application mobile sécurisée destinée aux infirmiers libéraux titulaires et aux infirmiers remplaçants. L’objectif est de faciliter la mise en relation professionnelle, la recherche de remplacements, la gestion des candidatures, les transmissions sécurisées et l’utilisation d’une assistance IA pour la transcription vocale.

---

## 1. Présentation du projet

Les infirmiers libéraux doivent assurer la continuité des soins, notamment en cas d’absence, de congé, de maladie ou de surcharge d’activité. Aujourd’hui, la recherche de remplaçants repose souvent sur des outils généralistes ou informels, peu adaptés aux contraintes du secteur médical.

INFIRMO propose une plateforme mobile spécialisée permettant :

- la création de profils professionnels infirmiers et cabinets ;
- la recherche de remplacements selon la zone, les disponibilités et les critères métier ;
- la publication d’offres de remplacement ;
- la gestion des candidatures et des statuts de mission ;
- la communication sécurisée entre professionnels ;
- la transcription vocale assistée par IA ;
- la prise en compte des contraintes RGPD, sécurité et hébergement HDS.

---

## 2. Dépôt GitHub

Ce dépôt est le dépôt principal du projet :

```text
EpitechMscProPromo2027/T-ESP-901-NCY-9-1-T-ESP-901-1
```

Il sert de mono-repo pour centraliser :

- la documentation projet ;
- les livrables ;
- le code applicatif ;
- la configuration DevOps ;
- le suivi technique du projet.

La structure est en place. Le périmètre fonctionnel actuel et ses limites sont décrits en tête de ce README.

Structure :

```text
.
├── README.md
├── CONTRIBUTING.md
├── docs/
│   └── livrables/
│       └── maquettes/
├── mobile/
├── backend/
├── ia/
└── infra/
```

Les dossiers `mobile/`, `backend/`, `ia/` et `infra/` contiennent leurs sources et leur documentation technique.

---

## 3. Modules du projet

| Module | Rôle |
| ------ | ---- |
| `mobile/` | Application mobile Flutter destinée aux infirmiers titulaires et remplaçants. |
| `backend/` | API backend, authentification, profils, remplacements, matching, messagerie et logique métier. |
| `ia/` | Service IA pour la transcription vocale et l’extraction d’informations. |
| `infra/` | Docker, CI/CD, déploiement, monitoring et configuration DevOps. |
| `docs/` | Cahier des charges, livrables, maquettes et documentation projet. |

---

## 4. Livrables

Les livrables principaux du projet sont centralisés dans le dossier `docs/livrables/`.

| Livrable | Emplacement / support | Échéance |
| -------- | --------------------- | -------- |
| Cahier des charges | `docs/livrables/` | Juin 2026 |
| Maquettes UI/UX MVP | `docs/livrables/maquettes/` + lien Figma | Juin 2026 |
| Backlog GitHub Projects | GitHub Projects | Juin 2026 puis suivi continu |
| README principal | `README.md` | Juin 2026 |
| Conventions projet | `CONTRIBUTING.md` | Juin 2026 |
| Documentation technique | README par module + `docs/` | Mars 2027 |
| Application mobile MVP | `mobile/` | Avril 2027 |
| Backend API | `backend/` | Avril 2027 |
| Service IA | `ia/` | Avril 2027 |
| Infrastructure / DevOps | `infra/` | Avril 2027 |
| Support de soutenance | Slides + démonstration | Avril 2027 |

---

## 5. Maquettes UI/UX

Les maquettes UI/UX du MVP sont réalisées dans Figma. Elles sont accessibles via un lien partagé depuis le dépôt GitHub du projet, dans le dossier :

```text
docs/livrables/maquettes/
```

Le fichier Figma constitue la référence visuelle pour la conception de l’application mobile et sert de support aux échanges de conception, à la validation des parcours utilisateurs et à l’implémentation progressive des écrans Flutter.

---

## 6. Organisation du projet

Le projet est suivi avec **GitHub Projects**.

Les tickets du backlog reprennent le backlog consolidé du cahier des charges. Chaque ticket est rattaché à un responsable, une estimation en jours-hommes, une priorité, un epic, un code WBS et, lorsque cela s’applique, une fonctionnalité ou user story du cahier des charges.

Workflow utilisé :

```text
To Do → In Progress → In Review → Done
```

---

## 7. Milestones et sprints

Le projet est suivi à deux niveaux complémentaires.

Les **milestones M1 à M6** correspondent aux grands jalons fonctionnels et documentaires du projet. Ils structurent la roadmap macro.

Les **sprints** correspondent aux cycles opérationnels de travail dans GitHub Projects. Le champ `Sprint` permet d’indiquer dans quel cycle un ticket est traité.

| Niveau | Usage |
| ------ | ----- |
| Milestone | Suivi macro du projet et des livrables : M1 à M6. |
| Sprint | Suivi opérationnel des tickets par cycle de travail effectif. |
| Start date / Target date | Dates utilisées pour l’affichage Roadmap dans GitHub Projects. |

Un ticket peut donc appartenir à un milestone fonctionnel tout en étant traité dans un sprint précis.

---

## 8. Planning macro

| Milestone | Période | Objectif principal | Livrable clé |
| --------- | ------- | ----------------- | ------------ |
| M1 - Spécifications | Fév. - Juin 2026 | Cahier des charges, maquettes Figma, backlog, architecture, préparation du dépôt | Docs + maquettes + backlog |
| M2 - MVP Core | Sept. - Nov. 2026 | Authentification, profils, documents, matching, socle mobile/backend | MVP fonctionnel |
| M3 - Remplacements | Déc. 2026 | Publication de tournées, candidatures, calendrier, statuts de mission | Module remplacements |
| M4 - Communication | Oct. 2026 - Jan. 2027 | Messagerie sécurisée, transmissions, vocaux, transcription IA, notifications | Module communication |
| M5 - Mobile & IA | Fév. - Mars 2027 | Tests, intégration, optimisation mobile/backend/IA, stabilisation | App mobile + IA stabilisées |
| M6 - Sécurité & Deploy | Mars 2027 | Sécurité, RGPD, HDS, déploiement candidat, documentation finale | Version candidate avant réserve |
| Réserve | Avril 2027 | Corrections, stabilisation, ajustements finaux et soutenance | Démo finale + soutenance |

---

## 9. Sprints de travail

| Sprint | Période | Objectif opérationnel |
| ------ | ------- | -------------------- |
| Sprint 1 | 11/09/2026 - 24/09/2026 | Socle technique et incrément synthétique connexion/profil persistant; tests, installation indépendante, Delta Log et reporting T9. Voir les limites et gates dans `reporting/sprint-1.md`. |
| Sprint 2 | 25/09/2026 - 27/11/2026 | Développement MVP Core : authentification, profils, documents, matching, premières intégrations. |
| Sprint 3 | 30/11/2026 - 22/01/2027 | Remplacements et communication : candidatures, calendrier, messagerie, transmissions, IA. |
| Sprint 4 | 29/01/2027 - 05/03/2027 | Tests, intégration, sécurité, optimisation et stabilisation de l’application. |
| Sprint 5 | 12/03/2027 - 19/03/2027 | Clôture opérationnelle : documentation technique, passation, livraison candidate. |

Avril 2027 est conservé comme réserve de finalisation. Cette période permet d’absorber les retards éventuels, de corriger les anomalies, de stabiliser la démonstration et de préparer la soutenance.

---

## 10. Équipe

| Membre | Rôle |
| ------ | ---- |
| Tetiana Lombardi | Cheffe de projet / UI-UX |
| Maxence Noizet | Dev Mobile Flutter |
| Yohan Baechlé | Dev Fullstack |
| Louis Chenot | Dev Backend |
| Ziad Tiarimti | Dev Backend |
| Pierre-Arthur Toutouom Yountebo | Dev IA |
| Lazaro Marrero Rousse | DevOps |

---

## 11. Stack technique prévue

| Couche | Technologie |
| ------ | ----------- |
| Mobile | Flutter |
| Backend | FastAPI |
| Base de données | PostgreSQL + PostGIS |
| Temps réel | WebSocket + Redis pub/sub |
| IA | Whisper |
| Conteneurisation | Docker |
| CI/CD | GitHub Actions |
| Maquettes | Figma |

---

## 12. Contribution

Les règles de contribution sont décrites dans [`CONTRIBUTING.md`](CONTRIBUTING.md).

Ce document précise notamment :

- les conventions Git ;
- le workflow des Pull Requests ;
- la gestion des tickets GitHub Projects ;
- les champs utilisés dans le backlog ;
- les règles de sécurité ;
- les conventions de code ;
- la Definition of Done.

---

## 13. Références projet

- Cahier des charges INFIRMO v4
- GitHub Projects du projet
- Maquettes Figma du MVP
- `CONTRIBUTING.md`
