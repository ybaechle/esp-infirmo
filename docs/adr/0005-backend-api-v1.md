# ADR 0005 - API backend v1 : sessions, chiffrement, audit et fournisseurs externes

Date : 2026-10-10. Statut : proposé, revue humaine requise avant fusion.

## Contexte

L'ADR 0003 limitait le backend à une démonstration synthétique (connexion, profil) et laissait ouverte la décision d'authentification du ticket LC-2. Les tickets backend du M2 au M5 (ZT-1 à ZT-11, LC-1 à LC-10, YB-1 à YB-9) demandent l'application complète : inscription, profils, offres, matching, candidatures, messagerie, transmissions, conformité. Les routes de démonstration (`/api/auth/*`, `/api/profile`) servent encore le mobile et `infra/check_v01.py`.

## Décision

**API versionnée en `/api/v1`**, à côté de la démonstration qui reste isolée derrière `INFIRMO_DEMO_MODE`. Contrat publié dans `docs/api/openapi.json` et comparé au code par un test. Toute erreur est `{detail, code}` : le mobile se branche sur `code`. Les listes sont paginées par `limit`/`offset` avec un ordre déterministe.

**Sessions** : jetons opaques aléatoires (256 bits), conservés hachés (SHA-256) ; accès de 15 minutes, refresh de 7 jours **à rotation** avec détection de réutilisation (un refresh rejoué révoque toute la famille). Le statut du compte est contrôlé à chaque requête. Les tentatives de connexion sont limitées par compte et par IP dans Redis, avec refus par défaut si Redis est indisponible. Cette décision ferme celle laissée ouverte par l'ADR 0003 pour LC-2.

**Autorisation côté serveur** : rôle (`titulaire`, `remplacant`), administrateur, appartenance au cabinet. Une ressource hors périmètre répond 404 pour ne pas révéler son existence.

**Chiffrement au repos** : AES-256-GCM avec trousseau de clés identifiées (rotation sans migration immédiate). Chiffrés : identité des patients, transmissions, corps et transcriptions des messages, fichiers (documents, photos, vocaux). Les colonnes portent leur contexte (`table.colonne`) en données authentifiées : un chiffré déplacé ne se lit plus. Sans clé configurée, l'écriture est refusée (503) plutôt que faite en clair.

**Audit** : table append-only (trigger PostgreSQL interdisant `UPDATE` et `DELETE` pendant 365 jours), sans donnée personnelle ni contenu. Les lectures de transmissions, téléchargements, refus d'accès, connexions et décisions d'administration y sont tracés.

**Conformité** : consentement explicite à l'inscription et à la création d'un patient ; transmissions supprimées après 30 jours par une commande planifiable (`python -m app.purge`), jamais par une requête ; droit à l'oubli du compte et d'un patient ; export JSON des données.

**Temps réel** : WebSocket authentifié par un premier message (le jeton n'est pas dans l'URL), diffusion par Redis pub/sub, événements limités aux identifiants. La diffusion est au mieux ; l'API REST reste la source de vérité.

**Fournisseurs externes non branchés** : e-mail/SMS pour la 2FA, push FCM/APNs, API publique de l'Ordre, transcription (service `ia/`). Chacun est une interface avec une implémentation absente ou simulée. `AGENTS.md` impose une revue de résidence des données et un contrat de sous-traitance avant tout fournisseur : l'application échoue explicitement (503) plutôt que d'envoyer des données ailleurs ou de simuler un succès.

## Alternatives écartées

- **JWT signés** : conformes à la lettre de LC-2 mais irrévocables avant expiration et dépendants d'une bibliothèque de plus ; la révocation immédiate prime pour des données de santé.
- **Géocodage et cartes côté serveur** : un service externe reçoit des adresses ; les coordonnées sont fournies par l'application mobile.
- **Chiffrement de bout en bout** (F4.1) : exige des clés sur les appareils et une gestion de récupération ; non livré, voir conséquences.
- **Files de tâches pour la purge** : un `cron` ou une tâche Compose suffit à ce volume.

## Conséquences

- Le chiffrement livré est **au repos côté serveur**, pas de bout en bout : le serveur peut lire les messages. Le cahier des charges (F4.1) demande plus ; la conception avec l'équipe mobile reste à faire.
- La 2FA, le push et la vérification de l'Ordre sont inopérants tant que leur fournisseur n'est pas choisi et validé. Le contrat attendu du service IA (`POST /transcribe`) doit être confirmé avec son responsable.
- Le classement du matching porte sur les 300 offres les plus proches, avec des pondérations fixes (proximité 35 %, disponibilités 30 %, CA 20 %, soins 15 %) à calibrer sur des données réelles.
- L'extension PostGIS est créée par migration : le rôle de la base doit pouvoir créer des extensions ou l'hébergeur doit la fournir.
- La purge n'est planifiée nulle part par défaut : sans tâche `cron`, la durée de conservation de 30 jours n'est pas garantie côté stockage (elle reste appliquée à la lecture).
- Les clés de chiffrement perdues rendent les données illisibles : leur sauvegarde séparée de la base est un prérequis d'exploitation.

Sources : `backend/app/`, `backend/tests/`, `docs/api/`, `AGENTS.md`.
