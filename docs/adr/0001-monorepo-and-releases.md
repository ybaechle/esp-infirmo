# ADR 0001 - Modules et versions indépendantes

Date de consignation : 2026-09-15. Statut : adopté, décision existante consignée rétrospectivement.

## Contexte

Le dépôt contient Flutter, FastAPI, un service IA privé et l'infrastructure. Le cahier des charges décrit un versionnement global, tandis que les manifestes de release existants publient des versions par module.

## Décision

Conserver le mono-repo et les tags `backend-vX.Y.Z`, `mobile-vX.Y.Z`, `ia-vX.Y.Z`. Le backend est le seul propriétaire des accès PostgreSQL/Redis; le mobile appelle le backend, et le backend appelle l'IA privée. La livraison académique v0.1 est identifiée par son commit testé et les versions des modules, sans nouveau tag global.

## Alternatives et conséquences

Des dépôts séparés compliqueraient les modifications coordonnées et le clone unique. Une version globale demanderait une migration inutile du mécanisme existant. Les versions indépendantes imposent d'enregistrer une combinaison cohérente des images/configurations déployées et de ne pas assimiler une release IA à une nouvelle fonctionnalité mobile.

Sources : `mobile/package.json`, `backend/package.json`, `ia/package.json`, `.github/workflows/release.yml`, `AGENTS.md`. Le champ de version seul ne prouve pas qu'une release a été construite ou validée.
