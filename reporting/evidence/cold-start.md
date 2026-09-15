# Reproduction technique avec caches vides — bf55fcd

**Résultat fonctionnel : réussi, avec deux corrections de l'outillage de vérification conservées.** Source `bf55fcd2dae591c1f8134aa989a388ce5f1ab7de`. Cette vérification technique automatisée ne constitue pas une validation par un pair humain extérieur.

## Environnement et portée

Clone distant neuf, README figé (SHA-256 du fichier Windows : `e7c53cc42a563c39f5f3d3c061b55f54d2b2126f999414e569388e5815d3dd87`). Docker Desktop 29.5.3 sur Windows, Python 3.13.6 déjà installé. Un conteneur Docker-in-Docker 29.8.0 / Compose 5.5.1 possède son propre stockage; aucun socket Docker hôte ni montage de sources n'est partagé. Ports de test 18080/18000, configurés selon l'option documentée du README.

Avant lancement : **0 image, 0 conteneur, 0 volume, 0 octet de cache de build** dans ce démon. Les historiques BuildKit identifient tous la révision figée : backend 16/16 étapes, IA 14/14, mobile 15/15, **0 % d'étapes en cache**. Durées BuildKit : backend 6 min03, IA 4 min43, mobile 18 min26. Les images backend, IA et web ont été construites au cours de la tentative d'origine.

## Sept actions du README

| Action | Observation | Temps disponible |
| --- | --- | --- |
| 1. Clone et révision | Clone distant réussi, HEAD bf55fcd | Clone 4,625 s |
| 2. Configuration | Copie neuve de `.env.example`, seuls ports documentés 18080/18000 | 0,213 s |
| 3. Validation Compose | Code 0 | 0,367 s |
| 4. Premier build et démarrage | Cinq services observés sains; BuildKit confirme les trois builds terminés | Fenêtre lancement→observation : 20 min 08,828 s; code de sortie original inconnu |
| 5. Acceptation API | Code 0 : accès anonyme refusé, connexion, modification/persistance, révocation | 21,334 s |
| 6. Interface Chrome 152 | Nom/ville/rôle sauvegardés, rechargement efface session, reconnexion conserve profil, déconnexion | 14:26:32–14:29:24 UTC, 172 s |
| 7. Arrêt/reprise et conservation | `down`, `up --wait`, connexion neuve/profil identique, `down`; codes 0 | Commandes 99,199 s; fenêtre 14:30:04–14:33:29 UTC |

L'interface froide a été vérifiée à **929×861**, dimension réelle de la capture après navigation; les vérifications 360/390 pixels appartiennent au contrôle distinct sur la pile en cache. Voir [capture du profil](cold-browser-profile.png).

Le profil synthétique modifié (`Camille Test Isolé`, `titulaire`, `Metz`) a conservé le digest `72a5b5d27e726e875431837e255e4aa4bc9bed655d2184f9015a83e14dbdf8d6` après arrêt complet/reprise et nouvelle connexion. Le profil initial a ensuite été restauré. Les volumes ont été conservés pendant ces sept actions.

## Frictions retenues et PDR borné

1. Le collecteur Windows a échoué avec `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f4ce' in position 10: character maps to <undefined>`. Configuration de stdout en UTF-8; le build Docker original a continué sans changement applicatif. Ses résultats ont été récupérés dans l'historique BuildKit. **Le code de sortie et l'instant précis de fin du premier Compose restent inconnus.**
2. Une saisie Playwright rapide après déconnexion n'a pas alimenté le contrôleur Flutter : délai d'attente, validation de mot de passe vide, aucune requête API. Saisie au clavier ciblée, distincte de la soumission : contrôle réussi.

**PDR de cette exécution des sept actions applicatives : 2/7 = 28,57 %.** Il inclut ces corrections du vérificateur pendant l'exécution. Il exclut la préparation préalable du dispositif ci-dessous et n'est donc pas le PDR de tout l'environnement. Aucune correction du code applicatif n'a été nécessaire sur cette révision.

## Préparation du dispositif, séparée du PDR

Prérequis Git/Python/Docker déjà installés; inventaire initial sans conteneur actif, environ 71,6 Gio libres sur C: et 383 Gio sur E:. Dispositif de test ajouté : conteneur `docker:29-dind --privileged` sans socket hôte (téléchargement/lancement 54,994 s), installation de `socat` (4,285 s), copie du clone vers `/work` (1,565 s), deux relais TCP depuis l'interface du conteneur vers ses ports loopback. Le script de collecte et les commandes exactes sont décrits dans [le relevé JSON](cold-start.json); les journaux séparent les actions `prerequisite-*`.

La fenêtre globale observée va de `2026-09-15T14:02:21.402402+00:00` à `2026-09-15T14:33:29.796491+00:00` : **1868.394 s**. Elle comprend préparation intercalée, pauses du vérificateur et contention d'un hôte partagé. **Ce n'est ni un benchmark sur matériel propre ni une mesure du temps d'un nouvel utilisateur.** Empreinte du démon après build : images 1,823 Go, cache 8,315 Go, volumes 113 Mo (catégories Docker pouvant partager des données).

## Preuves conservées

- [Commandes, horodatages, statuts et limites](cold-start.json).
- Journaux bruts, erreur initiale, README figé et historique BuildKit : `E:\Users\Moonie\Documents\School\Academic\Projects\infirmo-cold-bf55fcd`.
- Archive hors Git, sans clone ni `.env` : `cold-start-raw-bf55fcd.zip`; SHA-256 `9d3b8881a3d3eed5e07e74cacb868f47e09d6ee7681de0f9befcec19c5d2a9ec`.
- Toute régression ultérieure au commit 88a5abb avec ce cache est un contrôle distinct.
