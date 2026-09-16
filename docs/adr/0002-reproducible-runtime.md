# ADR 0002 - Exécution reproductible et schéma versionné

Date : 2026-09-15. Statut : adopté dans la livraison.

## Contexte

L'incrément doit être exécutable depuis un clone sans dépendance à un chemin local. La stack choisie comporte Flutter, FastAPI, PostgreSQL/PostGIS et Redis. Les procédures précédentes ne fournissaient pas de parcours utilisateur complet.

## Décision

Distribuer une interface web issue du même projet Flutter dans Compose pour l'exercice externe. Utiliser le proxy de même origine pour `/api`, des dépendances Python/Dart verrouillées et un SDK Flutter fixé. Conserver les dépendances privées dans le réseau Compose. Initialiser le schéma par Alembic et le compte fictif par une commande explicite, idempotente et interdite hors mode démonstration.

## Alternatives et conséquences

Un émulateur Android obligatoire augmenterait les prérequis de la soutenance. Une interface web distincte du projet Flutter doublerait le code. Une base SQLite en production divergerait de la stack validée : elle reste limitée aux tests unitaires, avec validation d'intégration PostgreSQL obligatoire. Les images et SDK peuvent nécessiter un téléchargement important; leur coût fait partie de la mesure à froid.

Le transport local en boucle locale est réservé aux données synthétiques. Il ne démontre ni chiffrement au repos, ni HDS, ni aptitude à recevoir des données réelles. L'installation staging utilise son propre TLS et sa configuration d'environnement.

Sources : `docker-compose.yml`, `backend/Dockerfile`, `backend/alembic.ini`, `mobile/Dockerfile`, `README.md`.
