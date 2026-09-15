# ADR 0003 - Compte fictif et profil persistant pour v0.1

Date : 2026-09-15. Statut : adopté dans la livraison, revue humaine requise avant fusion.

## Contexte

Le sprint 1 initial ne prévoyait que le socle technique. Le brief BUILD exige un sous-ensemble fonctionnel. Les lots d'authentification et de profil existent déjà au backlog M2, mais leur portée complète inclut des fonctionnalités non nécessaires à cette démonstration.

## Décision

Livrer connexion, lecture/modification d'un profil fictif et persistance après reconnexion. Activer les routes de démonstration uniquement avec `INFIRMO_DEMO_MODE=true`. Le compte initial utilise le domaine réservé `.example`. Le serveur contrôle l'identité du propriétaire à partir de la session; le client ne choisit pas un identifiant de profil à modifier.

Utiliser des jetons opaques aléatoires expirants, conservés hachés côté serveur et révocables à la déconnexion. Le client les conserve seulement en mémoire. Les mots de passe sont dérivés avec scrypt; les tentatives de connexion sont limitées. Les entrées sont bornées et les erreurs n'exposent pas le contenu des profils ni les secrets.

## Alternatives et conséquences

Un faux formulaire sans stockage ne validerait pas l'intégration. Déployer immédiatement l'inscription professionnelle, les refresh tokens, la 2FA et la vérification de l'Ordre dépasserait le sous-ensemble accepté. Les sessions opaques simplifient la révocation par rapport à des JWT autonomes; ce choix est limité à l'incrément synthétique et ne ferme pas la décision d'authentification complète du ticket LC-2.

L'utilisateur se reconnecte après fermeture/rechargement de l'application; les données de profil persistent dans PostgreSQL. Ce parcours ne termine pas les tickets parents MOB-2, YB-1 ou LC-2, et ne constitue pas une authentification de professionnels réels.

Sources : `backend/app/`, `backend/tests/`, `mobile/lib/`, `reporting/sprint-1.md`.
