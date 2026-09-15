# Installation à froid : protocole et preuve

**Validation indépendante : non réalisée.** Une vérification locale par l'auteur de la procédure ne remplace pas l'exécution par un pair.

Responsable de coordination : Yohan Baechlé. Date cible : 22 septembre 2026; reprise corrigée avant le 24 septembre. Le nom du testeur sera renseigné après son accord et son exécution.

## Conditions de départ

Utiliser une machine ou VM propre disposant seulement des prérequis publiés dans le README. Un nouveau dossier sur une machine disposant déjà des dépendances n'est pas une machine propre. Ne pas réutiliser `.env`, images applicatives, volumes, caches de compilation ou configuration locale non décrits. N'effacer aucun volume appartenant à un autre projet.

## Mesure

1. Consigner le système, ses versions, le testeur et l'heure de début. Choisir le commit à tester et figer ses instructions : toute modification impose une nouvelle exécution.
2. Suivre les étapes numérotées du [README](../README.md#installation-à-froid-v01) dans l'ordre, sans explication privée de l'équipe.
3. À chaque blocage, consigner la commande et la sortie utile dans le Delta Log. Retirer secrets et données personnelles avant d'enregistrer la preuve. Arrêter cette tentative; corriger le script ou document source par PR.
4. Reprendre sur un environnement propre au nouveau commit. Garder la première tentative dans `runs.csv` avec son propre résultat et son propre PDR.
5. Terminer lorsque le parcours interface connexion/modification/déconnexion/reconnexion conserve le profil et que le contrôle d'acceptation réussit. Consigner l'heure de fin, la durée et les résultats.

## Fiche à renseigner après exécution

| Champ | État |
| --- | --- |
| Testeur indépendant | Non désigné |
| Date, début et fin | Non mesurés |
| Système et versions | Non mesurés |
| Commit testé | Non désigné |
| Numéro de tentative | Non mesuré |
| Actions de référence / ajustements | Non mesurés |
| Installation, build, API et interface | Non validés indépendamment |
| Réouverture et persistance PostgreSQL | Non validées indépendamment |
| Delta Log et preuve de reprise | À relier aux exécutions réelles |

Ce tableau est une fiche d'attente, pas une attestation. Après l'exercice, remplacer les états par les observations et obtenir la validation écrite du testeur sur le résultat enregistré.
