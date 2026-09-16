# ADR 0004 - Mesures vérifiables et contrôle obligatoire

Date : 2026-09-15. Statut : adopté dans la livraison.

## Contexte

Des configurations existent sans preuve d'exécution. Certains workflows pouvaient réussir sans application ou déploiement. Les heures réelles, le PDR et l'installation indépendante n'étaient pas mesurés.

## Décision

Conserver les mesures sources en CSV/JSON sous `reporting/` et générer le tableau de bord avec Python standard. Maintenir un contrôle CI obligatoire sans filtre de chemin, des tests réels, des rapports de couverture et une validation Compose du parcours. Les résultats ignorés, bloqués ou non mesurés ne deviennent jamais des succès.

Une tentative d'installation référence une procédure figée et garde son propre nombre d'actions. Une correction produit une nouvelle tentative. Les heures réelles proviennent des responsables; l'ETC est réestimé indépendamment de la consommation. Les estimations originales et les échecs sont conservés.

## Alternatives et conséquences

Une application de dashboard supplémentaire n'apporte rien à ce sprint; des rapports manuels sans données sources ne sont pas recalculables. Exiger directement des checks filtrés par chemin pourrait bloquer les PRs qui ne les déclenchent pas. Un contrôle stable simplifie la protection, mais l'administrateur doit réellement appliquer les rulesets et rétablir la capacité Actions.

Sources : `.github/workflows/`, `infra/github/rulesets/`, `reporting/dashboard.py`, `CONTRIBUTING.md`.
