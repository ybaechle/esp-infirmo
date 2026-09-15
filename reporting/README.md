# Reporting du sprint 1

Période : **11 au 24 septembre 2026**. Responsable de consolidation : **Tetiana Lombardi**, travail **PM-4** du cahier des charges.

## Documents

- [Tableau de bord calculé](dashboard.md) : généré à partir des fichiers de mesures.
- [Effort](effort.csv) : estimations du cadrage, heures réelles et reste à faire.
- [Delta Log](delta-log.csv) : écarts observés, corrections et résultats de reprise.
- [Exécutions](runs.csv) : dénominateur et ajustements de chaque procédure mesurée.
- [Installation indépendante](onboarding.md) : protocole, preuves et statut de validation.
- [Bilan, roadmap et actions](sprint-1.md) : suivi humain et arbitrages.
- [ADRs](../docs/adr/README.md) : décisions techniques structurantes.

## Mise à jour quotidienne

1. Chaque responsable renseigne ses heures réellement passées et réestime le reste à faire dans `effort.csv`. Une cellule vide signifie **inconnu**, jamais zéro. L'estimation initiale du cadrage ne se réécrit pas.
2. Dès qu'une procédure bloque, conserver l'action prescrite, l'erreur observée, la correction et le document affecté dans `delta-log.csv`. Ajouter une nouvelle exécution après correction, sans supprimer la précédente.
3. Actualiser les preuves GitHub et recalculer :

   ```bash
   python reporting/dashboard.py --refresh-github
   python reporting/dashboard.py
   python -m unittest discover -s reporting -p "test_*.py"
   ```

   La première commande nécessite Python 3.12+, GitHub CLI et un accès en lecture au dépôt. Elle ne change ni les tickets ni les paramètres GitHub. Sans accès réseau, la deuxième commande utilise le dernier instantané daté.
4. Joindre les rapports de tests/couverture et le commit testé dans `evidence/`, sans jetons, mots de passe ou données personnelles. Les données de démonstration sont fictives.
5. Mettre à jour les décisions/actions de `sprint-1.md` et le ticket correspondant. Les fichiers sont un instantané versionné; GitHub Projects reste le suivi opérationnel quand son emplacement est confirmé.

## Définitions

- **1 JH = 7 h**, cahier des charges v4, page imprimée 26.
- **PDR/TDP** = ajustements manuels non prescrits / actions de référence prescrites × 100. Une action est une étape numérotée du protocole figé au commit testé. Un choix explicitement documenté n'est pas une dérive. Ne pas additionner les corrections de conception détectées par audit aux actions d'une installation qui n'a pas eu lieu.
- **Écart d'effort** = heures réelles + ETC réestimé − estimation initiale. Pour une tâche terminée, ETC = 0. Le pourcentage n'existe que si l'estimation initiale est strictement positive.
- **ETC** = estimation actuelle du travail restant, indépendante du temps déjà consommé.
- **Vélocité** = somme des estimations initiales des tâches engagées dans le sprint et réellement `Done`, comparée à la charge engagée. Une sous-partie démontrée ne termine pas le ticket parent.
- **CI** : conserver la période, le dépôt, la branche et le commit; distinguer succès, échecs exécutés, blocages d'infrastructure, exécutions en cours et étapes ignorées.
- **Couverture** : pourcentage mesuré avec périmètre, commande et commit; cible backend ≥ 70 %. La couverture du squelette IA ne démontre aucune transcription.
- **Réunions** : durée réelle × nombre de participants / 60 = heures-personnes. Conserver décisions et coût, pas seulement présence.

Les estimations du cadrage portent sur des tickets complets. Ne pas les présenter comme une allocation de sprint validée ni comme une mesure d'effort de cette livraison. Les heures humaines et l'ETC attendent les déclarations des responsables; les dates des actions sont des échéances de suivi, pas des promesses d'acceptation par des personnes absentes.
