# POC HDS — hébergement de données de santé (INF-12)

Ce document répond au ticket INF-12 (« POC HDS ») : il explique pourquoi
l'hébergement actuel n'est **pas** un hébergement de données de santé (HDS),
ce que la loi exige, et la cible recommandée pour quand INFIRMO manipulera de
vraies données de santé (patients, transmissions, voix). Il complète la skill
`hds-hosting` et AGENTS.md, qui restent la référence normative.

---

## 1. Décision intérimaire

**L'équipe n'achète pas d'hébergeur certifié HDS pour le moment** (budget
DevOps de 21 JH, projet étudiant). L'hébergement intérimaire est un **serveur
Docker classique, non certifié HDS** (voir `infra/deploy/`), utilisé comme
environnement **staging**.

**Cet environnement staging ne doit contenir que des données SYNTHÉTIQUES.**
Ce n'est pas une préférence ou une bonne pratique optionnelle : c'est une
obligation légale. Art. L.1111-8 du Code de la santé publique impose la
certification HDS à quiconque héberge des données de santé à caractère
personnel recueillies à l'occasion d'activités de prévention, de diagnostic,
de soin ou de suivi médico-social. **Aucune donnée de santé réelle** (profils
infirmiers réels, transmissions liées à un patient, enregistrements vocaux
réels) ne doit transiter par ce serveur, y compris temporairement, y compris
en test. Voir AGENTS.md-5.3 et la skill `hds-hosting`.

En pratique :

- Fixtures de test, seeds de démo, comptes de démonstration : générés
  synthétiquement (voir AGENTS.md).
- `docker-compose.staging.yml` est structurellement identique à ce qui sera
  déployé plus tard sur un hébergeur certifié (voir §4) — seul le contenu de
  `.env` et l'hébergeur changent au moment de la bascule.

## 2. Obligations légales résumées

| Sujet | Référence | Ce que ça impose |
| ----- | --------- | ----------------- |
| Certification obligatoire | Art. **L.1111-8** CSP (Loi 2016-41 du 26 janvier 2016) | Tout hébergeur de données de santé à caractère personnel doit détenir un certificat de conformité HDS. |
| Procédure de certification | Décret **2018-137** (26 février 2018) | Certificats délivrés par des organismes accrédités **COFRAC** (Bureau Veritas, AFNOR, BSI…). |
| Référentiel applicable | Arrêté du **26 avril 2024** (référentiel v2.0) | La période de transition de 24 mois s'est achevée le **16 mai 2026** : tout certificat doit désormais être en **v2.0** (vérifier qu'un hébergeur candidat n'est pas resté en v1.1 légataire). |
| Activités certifiables | Art. **R1111-9** CSP | 6 activités (voir §3) ; un hébergeur peut n'être certifié que sur certaines d'entre elles. |
| Résidence des données | Exigence **28** du référentiel v2.0 | Stockage exclusivement dans l'**EEE** (UE + Islande, Norvège, Liechtenstein), y compris par les **sous-traitants** de l'hébergeur. Pas de bucket, de log ni de sauvegarde en région US. |

Les **6 activités certifiables** (Art. R1111-9 CSP) :

| # | Activité |
| - | -------- |
| 1 | Mise à disposition de site physique |
| 2 | Infrastructure matérielle (physique) |
| 3 | Infrastructure virtuelle |
| 4 | Plateforme applicative (hébergement d'applications) |
| 5 | Administration et exploitation du système d'information |
| 6 | Sauvegarde externalisée / archivage |

> **Point de vigilance : les sauvegardes sont l'activité 6.** Un hébergeur
> "certifié HDS" ne couvre pas forcément les backups — il faut vérifier
> explicitement que l'activité 6 est incluse, sinon les sauvegardes de
> INFIRMO ont besoin d'un dispositif certifié séparé.

## 3. Cible recommandée

| Hébergeur | Depuis | Version | Activités | Souveraineté |
| --------- | ------ | ------- | --------- | ------------- |
| **OVHcloud** — **recommandé** | 2019 | v2 | Activités complètes (Hosted Private / Public / Bare Metal) | 🇫🇷 souverain (France) |
| Scaleway — alternative | juil. 2024 | v2 | Instances & Kapsule : activités 1-5 ; stockage : 1-4 ; bare metal : 1-2 — **pas l'activité 6** | 🇫🇷 souverain (SecNumCloud en cours) |
| AWS / Azure / GCP | — | certifiés | Selon offre | ⚠️ à capitaux US — risque **CLOUD Act** |

- **Cible recommandée : OVHcloud**, VM HDS avec les **6 activités**
  couvertes (y compris la sauvegarde externalisée, activité 6) — évite d'avoir
  à contractualiser un dispositif de backup séparé, et reste souverain
  (hébergeur français, pas d'exposition CLOUD Act).
- **Alternative : Scaleway**, à condition de couvrir explicitement l'activité
  6 (sauvegarde) par un autre moyen certifié, puisque l'offre actuelle
  Scaleway ne la couvre pas.
- **AWS/Azure/GCP** sont certifiés HDS v2.0 mais restent des entités à
  capitaux américains : même hébergées en région EEE, elles exposent les
  données au **CLOUD Act** (droit d'accès extraterritorial américain). Ce
  n'est pas rédhibitoire légalement, mais c'est un **risque à documenter dans
  l'AIPD** (voir skill `french-health-data-compliance`) si un hyperscaler
  américain devait être retenu. Le niveau de garantie supérieur est la
  qualification **SecNumCloud** (ANSSI) ; à date, ni Scaleway ni OVHcloud ne
  l'ont obtenue pour l'offre visée, mais leur statut souverain limite déjà
  fortement le risque comparé aux hyperscalers américains.

> Cette liste a été vérifiée en **juillet 2026** à partir des sources
> primaires (Légifrance, ANS/esante.gouv.fr). Elle **doit être reconfirmée**
> sur la liste officielle et vivante avant toute contractualisation :
> <https://esante.gouv.fr/offres-services/hds/liste-des-hebergeurs-certifies>

### Responsabilités : hébergeur vs INFIRMO

La certification HDS garantit l'**environnement d'hébergement** (site,
infrastructure, exploitation, sauvegarde selon les activités souscrites).
Elle ne décharge pas INFIRMO de ses propres obligations en tant que
**responsable de traitement** :

- base légale du traitement et information des utilisateurs ;
- analyse d'impact (AIPD) sur les traitements à risque (voir
  `french-health-data-compliance`) ;
- contrôle d'accès applicatif (RBAC, journalisation — voir
  `secure-coding-sante`) ;
- gestion des clés de chiffrement ;
- **contrat de sous-traitance Art. 28 (DPA)** avec l'hébergeur avant toute
  donnée réelle (voir skill `dpa-sous-traitance`).

## 4. Chemin de migration

`infra/deploy/docker-compose.staging.yml` est conçu pour être redéployé
**tel quel** sur la future VM HDS : services, images, réseaux et healthchecks
ne changent pas. Seuls changent l'hébergeur, le contenu de `.env` (mots de
passe, domaine, images pinnées) et, potentiellement, le nom donné au fichier
sur le serveur cible. Le pipeline de déploiement (`infra/deploy/README.md`)
n'a donc pas à être réécrit au moment de la bascule.

**Checklist à valider avant de signer un contrat d'hébergement HDS** (avant
qu'une seule donnée de santé réelle ne transite) :

1. Vérifier l'hébergeur candidat **le jour même** sur la liste officielle ANS
   (esante.gouv.fr/offres-services/hds/liste-des-hebergeurs-certifies), pas
   sur la base de ce document (qui date de juillet 2026).
2. Vérifier qu'il couvre les **activités exactes** dont INFIRMO a besoin,
   y compris l'**activité 6** (sauvegarde) si les backups doivent être
   couverts par le même certificat.
3. Vérifier la **résidence EEE** des données — **y compris chez les
   sous-traitants** de l'hébergeur, pas seulement chez l'hébergeur lui-même.
4. **Contrat de sous-traitance Art. 28 (DPA) signé** avant toute donnée
   réelle (voir skill `dpa-sous-traitance`).
5. Si un hébergeur non-souverain (à capitaux US) est envisagé : **risque de
   souveraineté documenté dans l'AIPD** avant toute décision.

**Checklist technique à la bascule** (issue de la revue `compliance-reviewer`
du 2026-07-02) :

6. **Chiffrement au repos du volume PostgreSQL live** (pas seulement des
   backups) : aucune donnée de santé en clair au repos (AGENTS.md,
   skill `secure-coding-sante`) — chiffrement disque/volume côté hébergeur
   ou LUKS sur la VM, à valider avant toute donnée réelle.
7. **Épingler la clé d'hôte SSH** des serveurs de déploiement via un secret
   GitHub (`STAGING_SSH_KNOWN_HOSTS` / `PROD_SSH_KNOWN_HOSTS`) au lieu du
   `ssh-keyscan` à la volée (TOFU) utilisé en staging synthétique.
8. **Renommer ou surcharger le compose** en variante production explicite
   (ex. `docker-compose.production.yml` ou overlay) pour ne pas transporter
   les hypothèses « staging » sur un hôte traitant des données réelles.

## 5. Périmètre HDS futur

Une fois l'hébergement HDS contractualisé, l'intégralité du périmètre qui
stocke ou traite des données de santé doit y résider — aucun composant de
cette liste ne doit rester sur un hébergement non-HDS dès lors que des
données réelles y transitent :

- **`db`** — PostgreSQL/PostGIS (profils, transmissions, données de matching).
- **`backend`** — API FastAPI (traite les données en transit et vers `db`).
- **`ia`** — microservice Whisper self-hosted (les enregistrements vocaux
  sont des données de santé par défaut, voir AGENTS.md — pas
  d'envoi à une API IA externe sans DPA + dispositif compatible HDS).
- **Sauvegardes** — de `db` et de tout stockage objet, chiffrées, dans le
  même périmètre EEE/HDS (activité 6).
- **Logs** — de tous les services ci-dessus, avec la même contrainte de
  résidence ; rappel AGENTS.md : jamais de donnée de santé ni de secret
  dans les logs/métriques/traces, HDS ou non.

---

Voir aussi : skill `hds-hosting` (source normative détaillée), skill
`dpa-sous-traitance`, skill `french-health-data-compliance`,
[`infra/deploy/README.md`](../deploy/README.md) (déploiement staging actuel).
