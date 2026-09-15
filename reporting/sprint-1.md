# Sprint 1 - bilan d'exécution et plan correctif

Période : **11 au 24 septembre 2026**. Mise à jour : **15 septembre 2026**. Consolidation : **Tetiana Lombardi**, lot **PM-4**. Ce document est un état de travail; il ne prétend pas qu'une revue ou rétrospective collective a déjà eu lieu.

## Périmètre ajusté

La baseline du README prévoyait uniquement structure, conventions, Docker et CI au sprint 1. Le brief BUILD exige un incrément utilisable : une tranche synthétique connexion/profil persistant est donc avancée depuis M2. Elle mobilise des parties de MOB-1/MOB-2, LC-1/LC-2, YB-1/YB-4 et ZT-2; **aucun de ces tickets parents n'est déclaré terminé** par cette démonstration.

Acceptation fonctionnelle : connexion avec le compte fictif; lecture et modification du nom fictif, de la ville et du rôle; sauvegarde PostgreSQL; nouvelle connexion récupérant les valeurs; déconnexion révoquant la session; refus des accès non authentifiés et des entrées invalides.

Restent hors incrément : inscription de professionnels réels, vérification de l'Ordre, 2FA, documents, recherche/matching, remplacements, transmissions, Whisper et hébergement de données réelles. Les lots correspondants gardent leur estimation initiale et doivent être réestimés par leurs responsables, sans déduction automatique du temps de cette intervention.

## Données disponibles

- [83 estimations du cadrage](effort.csv), total contrôlé **147 JH = 1029 h**, hors réserve avril de 31,5 JH. Elles concernent le projet complet, pas l'engagement de ce sprint.
- [Budget individuel et capacite sources](evidence/workload-baseline.md) : **147 h planifiees par personne**, dont 137.9 h productives et 9.1 h de reunions arrondies; reserve distincte de 31.5 h par personne. Le PDF fournit donc les heures prevues, sans mesurer leur consommation.
- [KPI calculés](dashboard.md), [Delta Log](delta-log.csv), [preuves de vérification](evidence/verification.md).
- Les heures reelles consommees, ETC et engagements de sprint n'ont pas été fournis. Ils restent inconnus. Ne pas répartir la durée d'exécution des outils entre les membres.
- Au constat initial, seuls deux contributeurs humains sont visibles sous plusieurs identités dans l'historique importé. Les commits squashés ne mesurent pas l'effort réel; la répartition doit être corroborée par tickets, revues, conception et essais.
- Le dépôt courant n'a ni issues, ni PRs, ni milestones lors du constat. L'ancien GitHub Project n'a pas été inspecté faute de scope `read:project`. Il faut retrouver le suivi existant avant de recréer ou déplacer des tickets.

## Roadmap révisée

| Période | Résultat attendu | Condition de clôture |
| --- | --- | --- |
| 15-21 septembre | Incrément synthétique, documentation, migrations et contrôles automatisés | Parcours réel et tests au même commit; preuves conservées |
| 22-23 septembre | Installation indépendante puis reprise des écarts | Pair externe, machine propre, mesures et sources corrigées |
| 24 septembre | Revue, rétrospective et replanification | ETC actualisé par chaque responsable; actions nominatives datées |
| Sprint 2, 25 septembre-27 novembre | Poursuite de M2 : authentification complète, profils, documents et matching | Réestimation après la revue; ne pas considérer la démo comme ces lots terminés |
| Sprints 3-5 | Remplacements/communication puis intégration, sécurité et stabilisation | Jalons initiaux conservés, dates à réexaminer sur ETC réel |

La réserve d'avril reste une réserve de risque. L'absence d'ETC empêche pour l'instant de justifier quantitativement un maintien de toutes les dates; elle est signalée, pas masquée par une progression estimée.

## Actions correctives

Les responsables suivent les rôles du cadrage. Ces échéances sont inscrites au plan; elles ne constituent pas une déclaration de travail déjà réalisé ou d'accord individuel recueilli.

| Action | Responsable unique | Échéance (Europe/Paris) | Critère de fermeture |
| --- | --- | --- | --- |
| Rapprocher la capacite des cinq sprints avec le budget PDF et confirmer M6 mars/avril | Tetiana Lombardi | 16/09/2026 18:00 | Allocation de jours/tickets par sprint, reserve distincte et decision de roadmap sourcees |
| Retrouver le Project et relier le backlog courant | Tetiana Lombardi | 16/09/2026 18:00 | URL accessible, tickets/WBS, responsables et engagement du sprint vérifiés |
| Fournir les heures réelles et ETC de chaque tâche active | Tetiana Lombardi, consolidation | 16/09/2026 18:00 puis chaque jour projet | Déclarations des sept responsables; tableau recalculé |
| Faire débloquer le budget Actions et appliquer les rulesets | Lazaro Marrero Rousse | 17/09/2026 18:00 | Administrateur identifié; contrôles exécutés; relecture API des deux protections |
| Faire relire les choix d'authentification de démonstration | Louis Chenot | 18/09/2026 18:00 | Revue ADR 0003 et tests d'autorisation |
| Vérifier la migration et la persistance PostgreSQL | Ziad Tiarimti | 18/09/2026 18:00 | Migration à partir d'une base vide et reprise sans perte |
| Valider le parcours Flutter et les écrans sur appareil | Maxence Noizet | 21/09/2026 18:00 | Tests et essai appareil; limites web/Android explicites |
| Organiser le test à froid avec un pair extérieur | Yohan Baechlé | 22/09/2026 18:00 | Fiche onboarding complétée par le testeur |
| Relire les preuves IA sans assimiler santé du service à transcription | Pierre-Arthur Toutouom Yountebo | 22/09/2026 18:00 | Périmètre et métriques vérifiés |
| Corriger et rejouer les écarts d'installation | Lazaro Marrero Rousse | 23/09/2026 18:00 | Chaque écart a son commit, document source et nouvelle exécution |
| Réaliser revue et rétrospective, publier l'ETC et la roadmap ajustée | Tetiana Lombardi | 24/09/2026 18:00 | Compte rendu réel avec décisions, propriétaires et dates |

## Rituels et rétrospective

Baseline du cahier des charges, page imprimée 34 : daily **15 min** les jours travaillés; planification, revue et rétrospective **20 min chacune**. Les trois séquences peuvent occuper la réunion longue d'une heure prévue au budget. Enregistrer dates effectives, participants, durée et décisions; ne pas créer de comptes rendus rétroactifs imaginaires.

**Rétrospective : non tenue dans cette livraison.** Lors de la séance du 24 septembre, traiter :

1. Temps réel des réunions et décisions utiles : comparer les heures-personnes au budget.
2. Répartition : tâches, revues, intégration et essais effectivement effectués par chaque membre; ne pas utiliser le nombre de commits comme score de travail.
3. Documentation : quels écarts ont été découverts par un pair, combien de reprises et quel PDR ?
4. Pipeline : différencier incapacité de démarrer les jobs, défauts de code et déploiements non effectués.
5. Prévisions : ETC de chaque tâche active, capacité disponible, périmètre ou échéances modifiés et justification chiffrée.

Conserver le compte rendu réel ici avec date, participants, durée, ce qui a fonctionné, ce qui a coûté du temps et au plus trois améliorations prioritaires. Chaque amélioration doit devenir une action avec une personne responsable et une date ferme.
